"""Independent pandas C/Fraction/SQLite reconciliation without production imports."""

from pathlib import Path
from fractions import Fraction
from collections import Counter
import argparse, csv, hashlib, json, sqlite3
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def main(path):
    n = 0

    def require(ok, label):
        nonlocal n
        assert ok, label
        n += 1

    receipt = json.loads((ROOT / "data/capture_receipt.json").read_bytes())
    require(
        hashlib.sha256(path.read_bytes()).hexdigest() == receipt["sha256"],
        "native bytes",
    )
    frame = pd.read_csv(
        path, engine="c", dtype=str, keep_default_na=False, encoding="utf-8-sig"
    )
    require(frame.columns.tolist() == receipt["columns"], "native headers")
    db = sqlite3.connect(":memory:")
    db.execute("CREATE TABLE ids (rid TEXT,eid TEXT,y TEXT)")
    db.executemany(
        "INSERT INTO ids VALUES (?,?,?)",
        (
            (
                str(r.ID).strip(),
                str(r.establishment_ID).strip(),
                str(r.year_filing_for).strip(),
            )
            for r in frame.itertuples(index=False)
        ),
    )
    drec = set(db.execute("SELECT rid,y FROM ids GROUP BY rid,y HAVING count(*)>1"))
    dest = set(db.execute("SELECT eid,y FROM ids GROUP BY eid,y HAVING count(*)>1"))

    def numeric(v):
        try:
            return Fraction(v.strip())
        except (ValueError, ZeroDivisionError, AttributeError):
            return None

    def whole(v):
        x = numeric(v)
        return x.numerator if x is not None and x.denominator == 1 else None

    case_fields = [
        "total_deaths",
        "total_dafw_cases",
        "total_djtr_cases",
        "total_other_cases",
    ]
    type_fields = [
        "total_injuries",
        "total_skin_disorders",
        "total_respiratory_conditions",
        "total_poisonings",
        "total_hearing_loss",
        "total_other_illnesses",
    ]
    states = [
        "wrong_year",
        "malformed_industry",
        "other_industry",
        "other_size",
        "missing_identity",
        "duplicate_identity",
        "unknown_counts",
        "inconsistent_counts",
        "unknown_flag",
        "inconsistent_flag",
        "unknown_exposure",
        "nonpositive_exposure",
        "eligible",
    ]
    accounts = Counter({s: 0 for s in states})
    cells = Counter()
    sizes = {21: "20-99", 22: "100-249", 2: "20-249 unsplit"}
    for r in frame.to_dict("records"):
        industry = r["naics_code"].strip()
        size = whole(r["size"])
        group = None
        cases = hours = ""
        if whole(r["year_filing_for"]) != 2025:
            state = "wrong_year"
        elif not (len(industry) == 6 and industry.isascii() and industry.isdigit()):
            state = "malformed_industry"
        elif industry[:2] not in ["31", "32", "33"]:
            state = "other_industry"
        elif size not in sizes:
            state = "other_size"
        else:
            group = (industry[:2], sizes[size])
            rid, eid, y = (
                r[k].strip() for k in ["ID", "establishment_ID", "year_filing_for"]
            )
            values = [whole(r[k]) for k in case_fields + type_fields]
            flag = whole(r["no_injuries_illnesses"])
            exposure = numeric(r["total_hours_worked"])
            if not (
                rid.isascii() and rid.isdigit() and eid.isascii() and eid.isdigit()
            ):
                state = "missing_identity"
            elif (rid, y) in drec or (eid, y) in dest:
                state = "duplicate_identity"
            elif any(x is None or x < 0 for x in values):
                state = "unknown_counts"
            elif sum(values[:4]) != sum(values[4:]):
                state = "inconsistent_counts"
            elif flag not in [1, 2]:
                state = "unknown_flag"
            elif (flag == 1 and sum(values[:4]) == 0) or (
                flag == 2 and sum(values[:4]) != 0
            ):
                state = "inconsistent_flag"
            elif exposure is None:
                state = "unknown_exposure"
            elif exposure <= 0:
                state = "nonpositive_exposure"
            else:
                state = "eligible"
                cases = str(sum(values[:4]))
                hours = str(exposure)
        accounts[state] += 1
        if group is not None:
            cells[(*group, state, cases, hours)] += 1
        require(sum(accounts.values()) > 0, "native row classified")
    with (ROOT / "data/summary_cells.csv").open(encoding="utf-8", newline="") as f:
        saved = list(csv.DictReader(f))
    require(len(saved) == len(cells), "all sufficient cells")
    for r in saved:
        key = tuple(r[k] for k in ["industry", "size_class", "state", "cases", "hours"])
        require(
            cells.pop(key, None) == int(r["records"]), "exact native cell multiplicity"
        )
    require(not cells, "no omitted native cells")
    summary = json.loads((ROOT / "data/source_accounts.json").read_bytes())
    require(summary["national_rows"] == len(frame), "all national rows")
    require(
        summary["cohort_rows"] == sum(int(r["records"]) for r in saved),
        "cohort partition",
    )
    require(
        summary["national_accounts"] == dict(accounts),
        "complete national classification",
    )
    require(
        summary["duplicate_record_key_groups"] == len(drec)
        and summary["duplicate_establishment_key_groups"] == len(dest),
        "SQLite duplicate groups",
    )
    require(sum(accounts.values()) == len(frame), "disjoint complete accounts")
    result = dict(
        status="PASS",
        finite_conditions=n,
        national_rows=len(frame),
        cohort_rows=summary["cohort_rows"],
        sufficient_cells=len(saved),
        native_sha256=receipt["sha256"],
        projection_sha256=hashlib.sha256(
            (ROOT / "data/summary_cells.csv").read_bytes()
        ).hexdigest(),
        pandas=pd.__version__,
        independent_method="pandas C parser,Fraction tokens,SQLite key multiplicities and complete native cell/account reconstruction;no production imports",
        scope="Current reported summary facts,not source truth,physical-establishment identity,worker risk or future accuracy.",
    )
    (ROOT / "data/native_verification.json").write_bytes(
        (json.dumps(result, indent=2) + "\n").encode()
    )
    print(json.dumps(result))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("source", type=Path)
    main(p.parse_args().source)
