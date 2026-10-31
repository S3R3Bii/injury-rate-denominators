"""Write a source-bound independent manuscript; distinguish fixed results and retrospective diagnostics."""

from pathlib import Path
from decimal import Decimal, localcontext
from fractions import Fraction
import csv, hashlib, json, shutil

ROOT = Path(__file__).resolve().parents[1]
bindings = []


def letters(index):
    result = ""
    while True:
        result = chr(65 + index % 26) + result
        index = index // 26 - 1
        if index < 0:
            return result


def load(file):
    if file.endswith(".csv"):
        with (ROOT / file).open(encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))
    return json.loads((ROOT / file).read_bytes())


def bind(file, field=None, query=None, operation="value"):
    value = load(file)
    if query is not None:
        rows = [r for r in value if all(r[k] == v for k, v in query.items())]
        assert len(rows) == 1
        value = rows[0]
    for key in field or []:
        value = value[key]
    if operation == "length":
        value = len(value)
    if operation == "commas":
        display = format(int(value), ",")
    elif operation.startswith(("percent", "decimal")):
        exact = Fraction(value) * (100 if operation.startswith("percent") else 1)
        with localcontext() as context:
            context.prec = 80
            display = format(
                Decimal(exact.numerator) / Decimal(exact.denominator),
                "." + operation[-1] + "f",
            )
    else:
        display = str(value)
    name = "Bound" + letters(len(bindings))
    bindings.append(
        dict(
            name=name,
            file=file,
            field=field,
            query=query,
            operation=operation,
            display=display,
        )
    )
    return "\\" + name + "{}"


def headline(field, op="commas"):
    return bind("results/summary.json", [field], operation=op)


def top(k, field, op="commas"):
    return bind(
        "results/exposure_concentration.csv", [field], dict(top_records=str(k)), op
    )


def checked(field):
    return bind("results/verification.json", [field], operation="commas")


p1 = (
    r"""\documentclass[11pt,letterpaper]{article}
\usepackage[margin=.72in]{geometry}
\usepackage[T1]{fontenc}
\usepackage{lmodern,microtype,booktabs,array,graphicx,pdflscape,xcolor,amsmath,hyperref}
\hypersetup{colorlinks=true,urlcolor=blue,linkcolor=blue,pdftitle={Reported injury rates depend on exposure}}
\setlength{\parindent}{0pt}\setlength{\parskip}{6pt}
\newcommand{\heading}[1]{\vspace{4pt}{\large\bfseries #1}\par}
%%BINDINGS%%
\begin{document}
{\LARGE\bfseries Reported injury rates depend on exposure\par}
\vspace{5pt}
Independent research program\hfill 31 October 2026 UTC\\
\textit{Not peer reviewed. Current submitted summary data; descriptive sensitivity.}

\heading{Practical finding}
A pooled injury rate can be dominated by a few reported exposure values. In this fixed manufacturing cohort, the five highest-hour records account for """
    + top(5, "share_of_hours", "percent2")
    + r"""\% of eligible reported hours, while carrying """
    + top(5, "top_cases")
    + r""" reported case. This concentration audit is explicitly retrospective: it was added after the frozen comparison exposed the denominator imbalance.

The full eligible cohort reports """
    + headline("total_cases")
    + r""" cases over """
    + headline("total_hours")
    + r""" hours, a pooled rate of """
    + headline("pooled_rate", "decimal6")
    + r""" per 100 full-time-equivalent worker-years. These are source-accounting values, not a validated population rate or evidence that the exposure values are correct. Both independent source parsers agree with the captured native values; that agreement does not establish source truth.

\heading{Recommended use}
Audit exposure concentration before using a pooled reported rate to center smoothing. A dashboard should retain the numerator, reported hours, missingness and smoothing assumptions. Seek source clarification for extreme exposure values before operational use. Do not silently cap or remove observations and call the result corrected.

The original source and all frozen estimates remain unchanged. Conditional rates after removing the highest-hour records are presented as accounting diagnostics, not cleaned estimates or a recommendation to delete those records. No employer identities or rankings are public.

\heading{Source and fixed scope}
The official OSHA 2025 Summary Data file contains """
    + headline("national_rows")
    + r""" rows. The fixed cohort retains """
    + headline("cohort_rows")
    + r""" manufacturing records in broad NAICS prefixes 31, 32 and 33 with reported maximum-size codes for 20--99, 100--249 or unsplit 20--249 employees. Annual average employment is not the size selector. """
    + headline("eligible_records")
    + r""" records have a consistent known numerator and positive reported hours; """
    + headline("nonpositive_exposure_records")
    + r""" nonpositive-hour records remain explicitly outside the rate denominator.

The numerical design was committed after the file was downloaded but before establishment values were parsed. Only the header, size and hash had been inspected. Values were visible during source reconciliation; this was source informed, not blinded. One current posted file does not establish original submission timing, physical-establishment identity or prediction-time availability.
\newpage
"""
)
p2 = r"""{\Large\bfseries Complete fixed accounts and conditional diagnostics\par}
{\small\setlength{\tabcolsep}{5pt}
\begin{tabular}{@{}llrrrrr@{}}\toprule
NAICS & Maximum size & Eligible & Excluded & Zero cases & Cases & Raw rate\\\midrule
"""
accounts = load("results/stratum_accounts.csv")
for row in accounts:
    q = {k: row[k] for k in ["industry", "size_class"]}
    parts = [row["industry"], row["size_class"]]
    for field in [
        "eligible_records",
        "unavailable_records",
        "zero_case_records",
        "total_cases",
    ]:
        parts.append(bind("results/stratum_accounts.csv", [field], q, "commas"))
    parts.append(
        bind("results/stratum_accounts.csv", ["pooled_raw_rate"], q, "decimal3")
    )
    p2 += " & ".join(parts) + r" \\" + "\n"
p2 += (
    r"""\bottomrule\end{tabular}}

Rates are reported cases per 100 full-time-equivalent worker-years, using 200,000 hours. Every fixed stratum is retained, including the unsplit legacy size class. NAICS versions can differ. Source-account categories, exact exposures and rates remain in the complete exports; no annual-average substitution or missing-to-zero fill is used.

\heading{All declared descriptive shrinkage strengths}
Let $t=h/200{,}000$ and $\mu=\sum k/\sum t$ across the complete eligible cohort. A Gamma--Poisson working model uses Gamma shape $b\mu$ and rate $b$, giving mean $(k+b\mu)/(t+b)$. The fixed prior exposures $b\in\{0.1,1,10\}$ span 20,000--2,000,000 hours. They are authored sensitivity probes, not tuned or empirically validated defaults. The center is estimated from this same cohort.

The authored boundary is rate $>2\mu$, with no regulatory or safety meaning. The raw rate exceeds it for """
    + headline("raw_above_twice_pooled_mean")
    + r""" records. At $b=0.1,1,10$, respectively, """
    + bind("results/summary.json", ["high_to_low", "1/10"], operation="commas")
    + r""", """
    + bind("results/summary.json", ["high_to_low", "1"], operation="commas")
    + r""" and """
    + bind("results/summary.json", ["high_to_low", "10"], operation="commas")
    + r""" move to at/below the boundary; none moves upward. All """
    + headline("sensitivity_cases")
    + r""" stratum/strength accounts and """
    + headline("cell_strength_cases")
    + r""" sufficient-cell/strength cases are exported. No winner is selected and no future accuracy is measured.

\heading{Retrospective concentration audit: all four cases}
{\small\setlength{\tabcolsep}{6pt}
\begin{tabular}{@{}rrrrr@{}}\toprule
Top records & Top cases & Hours share & Remaining hours & Conditional rate\\\midrule
"""
)
for k in [1, 5, 10, 100]:
    p2 += (
        " & ".join(
            [
                str(k),
                top(k, "top_cases"),
                top(k, "share_of_hours", "percent2") + r"\%",
                top(k, "remaining_hours"),
                top(k, "conditional_remaining_rate", "decimal3"),
            ]
        )
        + r" \\"
        + "\n"
    )
p2 += (
    r"""\bottomrule\end{tabular}}

All four conditional rates use the remaining submitted records. They are retrospective diagnostics, not replacement population estimates. The largest single reported exposure is """
    + bind(
        "results/exposure_diagnostic.json",
        ["maximum_single_record_hours"],
        operation="commas",
    )
    + r""" hours. No source error is asserted without clarification.

For zero recorded cases, $-\log(0.05)/t$ is the one-sided 95\% upper rate under a homogeneous independent Poisson process. All """
    + headline("zero_case_records")
    + r""" zero-case records and complete stratum bounds are retained. This assumption-based illustration has no measured interval calibration or workplace-safety validity.
\newpage
"""
)
p3 = (
    r"""{\Large\bfseries Verification, implementation and limits\par}
\heading{Independent evidence}
Separate pandas C parsing, SQLite key multiplicities and exact Fraction tokens reconcile all native rows in """
    + checked("native_source_conditions")
    + r""" finite conditions. Saved native-bound source checks pass """
    + checked("saved_source_conditions")
    + r""". Independent weighted SQLite and exact-rational reconstruction checks every account, cell/strength, strict boundary, switch direction and request in """
    + checked("independent_analysis_conditions")
    + r""" conditions. The retrospective record-expanded SQLite concentration audit passes """
    + checked("diagnostic_conditions")
    + r""" conditions.

The original committed freeze bound """
    + checked("original_frozen_dependencies")
    + r""" actual dependencies before comparisons. A disclosed post-analysis gzip-container amendment changes one writer, preserving every numeric result and the original code/freeze in HISTORY. Byte-preserving Git checkout fixes an inherited Windows line-ending failure. Both isolated full-history CPython """
    + bind("results/reproduction_cpython310.json", ["python"])
    + r""" and """
    + bind("results/reproduction_cpython312.json", ["python"])
    + r""" replays reproduce six files exactly, with all six source-directory files unchanged. Failed compatibility evidence is retained.

All """
    + checked("authored_fixture_methods")
    + r""" authored fixture methods pass, covering maximum versus average employment, documented injury-flag codes, duplicate groups, missing/invalid counts, zero/nonpositive hours, exact rate ties, prior strengths and unsupported inferences. The inspected figures bind """
    + bind("figures/verification.json", ["source_bound_artists"])
    + r""" actual SVG bars and """
    + bind("figures/verification.json", ["svg_coordinate_conditions"])
    + r""" coordinate conditions. Finite checks are not universal correctness guarantees.

\heading{Runnable implementation exercise}
Seven requests return two qualified reported-stratum accounts and reject safety ranking, legal fault, worker eligibility, future risk and denominator substitution. The interface retains numerator, exposure and explicit unknown safety/future accuracy. It does not certify arbitrary caller data or a production service.
\begin{verbatim}
python -m pip install -r requirements.txt
python src/replay.py --out ../injury-rate-replay
python src/check_diagnostics.py
\end{verbatim}
Use a new output directory. The replay uses saved counts; it does not redownload mutable native data.

\heading{Material limits and next evidence}
The original year-held-out partial-pooling proposal remains unexecuted. This is a same-cohort-centered descriptive sensitivity study, with no protected test, future-risk accuracy or new estimator. Source reporting, optional/nonrequired submissions, mixed industry-code versions and unknown physical-establishment identity limit generalization. Reporting does not establish fault, violation or benefit eligibility. No causal, production-use or realized-savings claim is made.

Raw establishment names, addresses, EINs, identifiers and native files remain private. No case-detail or worker data were requested. Separate formal-publication projects, including Azure optimization, remain private. Seek corrected or clarified exposure and verified identity/dated availability before a predictive extension.

{\small Source: OSHA Injury Tracking Application, 2025 Summary Data, submitted January--August 2026, captured 31 October 2026 UTC.
\url{https://www.osha.gov/itadata}.
Definitions: April 2024 Summary Data Dictionary and January 2025 ITA Data Users Guide. Exact URL, native hash, source accounts and earlier access failures are retained. OSHA does not endorse this independent analysis. MIT covers original code; government facts are attributed separately.}
"""
)
figs = []
for title, name in [
    ("Retrospective exposure concentration", "exposure_concentration"),
    ("Complete declared smoothing comparisons", "smoothing_sensitivity"),
    ("Complete source eligibility accounts", "source_denominators"),
]:
    figs.append(
        r"\begin{landscape}"
        + "\n"
        + r"{\large\bfseries "
        + title
        + r"\par}"
        + "\n"
        + r"\begin{center}\includegraphics[width=9.4in,height=6.25in,keepaspectratio]{images/"
        + name
        + r".pdf}\end{center}"
        + "\n"
        + r"\end{landscape}"
        + "\n"
    )
tex = p1 + p2 + p3 + "".join(figs) + r"\end{document}" + "\n"
tex = tex.replace(
    "%%BINDINGS%%",
    "\n".join(
        "\\newcommand{\\" + r["name"] + "}{" + r["display"] + "}" for r in bindings
    ),
)
paper = ROOT / "paper"
(paper / "images").mkdir(parents=True, exist_ok=True)
for name in ["exposure_concentration", "smoothing_sensitivity", "source_denominators"]:
    shutil.copy2(ROOT / "figures" / (name + ".pdf"), paper / "images" / (name + ".pdf"))
(paper / "main.tex").write_bytes(tex.rstrip().encode() + b"\n")
(paper / "bindings.json").write_bytes((json.dumps(bindings, indent=2) + "\n").encode())
print("SOURCE_BOUND_MANUSCRIPT_WRITTEN", len(bindings))
