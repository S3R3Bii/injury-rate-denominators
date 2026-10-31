"""Independently verify used manuscript values, complete tables and reviewed scope."""

from pathlib import Path
from decimal import Decimal, localcontext
from fractions import Fraction
import ast, csv, hashlib, json, re, unicodedata
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    if name.endswith(".csv"):
        with (ROOT / name).open(encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))
    return json.loads((ROOT / name).read_bytes())


def expected(binding):
    value = load(binding["file"])
    if binding["query"] is not None:
        matched = [
            r for r in value if all(r[k] == v for k, v in binding["query"].items())
        ]
        assert len(matched) == 1
        value = matched[0]
    for key in binding["field"] or []:
        value = value[key]
    op = binding["operation"]
    if op == "length":
        return str(len(value))
    if op == "commas":
        return format(int(value), ",")
    if op in ["percent2", "decimal3", "decimal6"]:
        exact = Fraction(value) * (100 if op.startswith("percent") else 1)
        with localcontext() as context:
            context.prec = 80
            return format(
                Decimal(exact.numerator) / Decimal(exact.denominator),
                "." + op[-1] + "f",
            )
    assert op == "value"
    return str(value)


def main():
    n = 0

    def require(ok, label):
        nonlocal n
        assert ok, label
        n += 1

    pdf = PdfReader(ROOT / "paper/manuscript.pdf")
    require(len(pdf.pages) == 6, "six current pages")
    pages = [unicodedata.normalize("NFKC", p.extract_text() or "") for p in pdf.pages]
    compact = re.sub(r"\s+", " ", "\n".join(pages))
    words = re.sub(r"([A-Za-z])-\s+([A-Za-z])", r"\1\2", "\n".join(pages))
    words = re.sub(r"\s+", " ", words)
    tex = (ROOT / "paper/main.tex").read_text(encoding="utf-8")
    bindings = load("paper/bindings.json")
    require(
        len(bindings) == 88 and len({b["name"] for b in bindings}) == len(bindings),
        "unique actual bindings",
    )
    for binding in bindings:
        value = expected(binding)
        require(value == binding["display"], "independent source value and format")
        require(
            "\\newcommand{\\" + binding["name"] + "}{" + value + "}" in tex,
            "actual definition",
        )
        require(
            len(re.findall(r"\\" + re.escape(binding["name"]) + r"\b", tex)) >= 2,
            "actually used beyond definition",
        )
        require(value in compact, "actual PDF value")
    table = re.sub(r"\s+", " ", pages[1])
    rows = load("results/stratum_accounts.csv")
    require(
        [(r["industry"], r["size_class"]) for r in rows]
        == [
            (i, s)
            for i in ["31", "32", "33"]
            for s in ["20-99", "100-249", "20-249 unsplit"]
        ],
        "all nine fixed strata",
    )
    for r in rows:
        parts = [r["industry"], r["size_class"]]
        parts += [
            format(int(r[k]), ",")
            for k in [
                "eligible_records",
                "unavailable_records",
                "zero_case_records",
                "total_cases",
            ]
        ]
        parts += [
            expected(
                dict(
                    file="results/stratum_accounts.csv",
                    query={"industry": r["industry"], "size_class": r["size_class"]},
                    field=["pooled_raw_rate"],
                    operation="decimal3",
                )
            )
        ]
        require(" ".join(parts) in table, "complete actual PDF stratum row")
    for r in load("results/exposure_concentration.csv"):
        q = {"top_records": r["top_records"]}
        parts = [
            r["top_records"],
            format(int(r["top_cases"]), ","),
            expected(
                dict(
                    file="results/exposure_concentration.csv",
                    query=q,
                    field=["share_of_hours"],
                    operation="percent2",
                )
            )
            + "%",
            format(int(r["remaining_hours"]), ","),
            expected(
                dict(
                    file="results/exposure_concentration.csv",
                    query=q,
                    field=["conditional_remaining_rate"],
                    operation="decimal3",
                )
            ),
        ]
        require(" ".join(parts) in table, "all retrospective conditional PDF rows")
    for phrase in [
        "Not peer reviewed",
        "explicitly retrospective",
        "not a validated population rate",
        "does not establish source truth",
        "source informed, not blinded",
        "not cleaned estimates",
        "not tuned or empirically validated defaults",
        "No winner is selected",
        "no measured interval calibration",
        "original year-held-out partial-pooling proposal remains unexecuted",
        "post-analysis gzip-container amendment",
        "No case-detail or worker data were requested",
        "Azure optimization",
        "does not endorse",
    ]:
        require(phrase.lower() in words.lower(), ("actual scope qualification", phrase))
    freeze = load("PLAN_FREEZE.json")
    require(len(freeze["hashes"]) == 21, "21 actual protected dependencies")
    original_path = ROOT / freeze["original_comparison_freeze"]
    require(
        hashlib.sha256(original_path.read_bytes()).hexdigest()
        == freeze["original_freeze_sha256"],
        "preserved original freeze bytes",
    )
    original = json.loads(original_path.read_bytes())
    require(
        [k for k in original["hashes"] if original["hashes"][k] != freeze["hashes"][k]]
        == ["src/analyze.py"],
        "only one disclosed packaging dependency changed",
    )
    old_code = (ROOT / "HISTORY/analyze_original.py").read_bytes()
    require(
        hashlib.sha256(old_code).hexdigest() == original["hashes"]["src/analyze.py"],
        "preserved original writer code",
    )

    def numerical_ast(data):
        tree = ast.parse(data)
        tree.body = [
            node
            for node in tree.body
            if not isinstance(node, ast.FunctionDef) or node.name != "write_csv"
        ]
        return ast.dump(tree)

    require(
        numerical_ast(old_code)
        == numerical_ast((ROOT / "src/analyze.py").read_bytes()),
        "all non-writer numerical syntax unchanged",
    )
    verification = load("results/verification.json")
    require(verification["authored_fixture_methods"] == 31, "31 authored fixtures")
    for name, digest in verification["result_sha256"].items():
        require(
            hashlib.sha256((ROOT / "results" / name).read_bytes()).hexdigest()
            == digest,
            "current output bytes",
        )
    for suffix in ["310", "312"]:
        replay = load("results/reproduction_cpython" + suffix + ".json")
        require(
            replay["status"] == "PASS" and replay["full_history"],
            "isolated full history",
        )
        require(
            len(replay["reproduced_files"]) == 6
            and replay["unchanged_source_files"] == 6,
            "actual replay scope",
        )
        require(
            replay["reproduced_files"] == list(verification["result_sha256"]),
            "six outputs",
        )
    scope = load("paper/PUBLICATION_SCOPE.json")
    require(
        scope["scope"] == "independent-program-study"
        and scope["formal_submission_target"] is False,
        "independent publication scope",
    )
    require(len(scope["public_files"]) == 5, "five scoped files")
    for name, digest in scope["public_files"].items():
        require(
            hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest,
            "current scoped bytes",
        )
    for name in [
        "exposure_concentration",
        "smoothing_sensitivity",
        "source_denominators",
    ]:
        require(
            (ROOT / "figures" / (name + ".pdf")).read_bytes()
            == (ROOT / "paper/images" / (name + ".pdf")).read_bytes(),
            "current figure copy",
        )
    visual = load("paper/visual_review.json")
    require(visual["pages_reviewed"] == [1, 2, 3, 4, 5, 6], "all pages reviewed")
    require(
        visual["manuscript_sha256"]
        == hashlib.sha256((ROOT / "paper/manuscript.pdf").read_bytes()).hexdigest(),
        "reviewed PDF bytes",
    )
    for name, digest in visual["reviewed_figure_png_sha256"].items():
        require(
            hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest,
            "reviewed figure bytes",
        )
    receipt = dict(
        status="PASS",
        finite_conditions=n,
        used_numeric_bindings=len(bindings),
        pages=len(pdf.pages),
        scope_files=5,
        scope="Used source bindings, complete stratum/diagnostic PDF tables, preserved original freeze and unchanged numerical AST, current output and figure hashes, two replay receipts, all rendered pages and approved independent publication scope. Finite evidence, not universal correctness.",
    )
    (ROOT / "paper/verification.json").write_bytes(
        (json.dumps(receipt, indent=2) + "\n").encode()
    )
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
