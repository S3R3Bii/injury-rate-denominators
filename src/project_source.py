"""Project minimal sufficient manufacturing summary counts; keep identities private."""

from pathlib import Path
from collections import Counter
from decimal import Decimal, InvalidOperation
from fractions import Fraction
import argparse, csv, hashlib, json

ROOT = Path(__file__).resolve().parents[1]
CASE_FIELDS = [
    "total_deaths",
    "total_dafw_cases",
    "total_djtr_cases",
    "total_other_cases",
]
TYPE_FIELDS = [
    "total_injuries",
    "total_skin_disorders",
    "total_respiratory_conditions",
    "total_poisonings",
    "total_hearing_loss",
    "total_other_illnesses",
]
STATES = [
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
SIZES = {"21": "20-99", "22": "100-249", "2": "20-249 unsplit"}


def number(value):
    try:
        result = Decimal(value.strip())
        return result if result.is_finite() else None
    except (InvalidOperation, AttributeError):
        return None


def integer(value):
    n = number(value)
    return int(n) if n is not None and n == n.to_integral_value() else None


def identity(row):
    return tuple(row[k].strip() for k in ["ID", "establishment_ID", "year_filing_for"])


def classify(row, duplicate_records, duplicate_establishments):
    year = integer(row["year_filing_for"])
    industry = row["naics_code"].strip()
    size = str(integer(row["size"]))
    if year != 2025:
        return "wrong_year", None
    if len(industry) != 6 or not industry.isascii() or not industry.isdigit():
        return "malformed_industry", None
    if industry[:2] not in ["31", "32", "33"]:
        return "other_industry", None
    if size not in SIZES:
        return "other_size", None
    group = (industry[:2], SIZES[size])
    rid, eid, rawyear = identity(row)
    if not rid.isascii() or not rid.isdigit() or not eid.isascii() or not eid.isdigit():
        return "missing_identity", group
    if (rid, rawyear) in duplicate_records or (
        eid,
        rawyear,
    ) in duplicate_establishments:
        return "duplicate_identity", group
    counts = [integer(row[k]) for k in CASE_FIELDS + TYPE_FIELDS]
    if any(v is None or v < 0 for v in counts):
        return "unknown_counts", group
    cases = sum(counts[:4])
    if cases != sum(counts[4:]):
        return "inconsistent_counts", group
    flag = integer(row["no_injuries_illnesses"])
    if flag not in [1, 2]:
        return "unknown_flag", group
    if (flag == 1) != (cases > 0):
        return "inconsistent_flag", group
    hours = number(row["total_hours_worked"])
    if hours is None:
        return "unknown_exposure", group
    if hours <= 0:
        return "nonpositive_exposure", group
    return "eligible", group + (str(cases), str(Fraction(hours)))


def main(path):
    receipt = json.loads((ROOT / "data/capture_receipt.json").read_bytes())
    assert (
        path.stat().st_size == receipt["bytes"]
        and hashlib.sha256(path.read_bytes()).hexdigest() == receipt["sha256"]
    )
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == receipt["columns"]
        rows = list(reader)
    assert all(None not in r and all(v is not None for v in r.values()) for r in rows)
    record_keys = Counter((identity(r)[0], identity(r)[2]) for r in rows)
    estab_keys = Counter((identity(r)[1], identity(r)[2]) for r in rows)
    duplicate_records = {k for k, n in record_keys.items() if n > 1}
    duplicate_establishments = {k for k, n in estab_keys.items() if n > 1}
    accounts = Counter({s: 0 for s in STATES})
    cells = Counter()
    for r in rows:
        state, group = classify(r, duplicate_records, duplicate_establishments)
        accounts[state] += 1
        if group is not None:
            if state == "eligible":
                industry, size, cases, hours = group
            else:
                industry, size = group
                cases = hours = ""
            cells[(industry, size, state, cases, hours)] += 1
    with (ROOT / "data/summary_cells.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(
            ["industry", "size_class", "state", "cases", "hours", "records"]
        )
        writer.writerows((*key, n) for key, n in sorted(cells.items()))
    summary = dict(
        national_rows=len(rows),
        cohort_rows=sum(cells.values()),
        sufficient_cells=len(cells),
        national_accounts=dict(accounts),
        duplicate_record_key_groups=len(duplicate_records),
        duplicate_establishment_key_groups=len(duplicate_establishments),
        source_sha256=receipt["sha256"],
        source_meaning="One current posted 2025 summary file;within-file identity defense only,no cross-year identity or prediction-time availability.",
    )
    (ROOT / "data/source_accounts.json").write_bytes(
        (json.dumps(summary, indent=2) + "\n").encode()
    )
    print(json.dumps(summary))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("source", type=Path)
    main(p.parse_args().source)
