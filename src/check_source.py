"""Verify the entire minimal source projection against its independent native receipt."""

from pathlib import Path
from collections import Counter
from fractions import Fraction
import csv, hashlib, json

ROOT = Path(__file__).resolve().parents[1]


def main():
    n = 0

    def require(ok, label):
        nonlocal n
        assert ok, label
        n += 1

    native = json.loads((ROOT / "data/native_verification.json").read_bytes())
    source = json.loads((ROOT / "data/source_accounts.json").read_bytes())
    require(native["status"] == "PASS", "independent native reconciliation")
    require(
        hashlib.sha256((ROOT / "data/summary_cells.csv").read_bytes()).hexdigest()
        == native["projection_sha256"],
        "native-bound cells",
    )
    require(source["source_sha256"] == native["native_sha256"], "native identity")
    with (ROOT / "data/summary_cells.csv").open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    signatures = set()
    states = Counter()
    for r in rows:
        key = tuple(r[k] for k in ["industry", "size_class", "state", "cases", "hours"])
        require(key not in signatures, "unique sufficient cell")
        signatures.add(key)
        require(r["industry"] in ["31", "32", "33"], "fixed manufacturing prefix")
        require(
            r["size_class"] in ["20-99", "100-249", "20-249 unsplit"],
            "documented maximum-employment size",
        )
        require(
            r["state"] in list(source["national_accounts"])[4:],
            "explicit cohort account",
        )
        require(int(r["records"]) > 0, "positive multiplicity")
        if r["state"] == "eligible":
            require(
                Fraction(r["cases"]).denominator == 1 and int(r["cases"]) >= 0,
                "known nonnegative integer count",
            )
            require(Fraction(r["hours"]) > 0, "known positive exposure")
        else:
            require(r["cases"] == r["hours"] == "", "unavailable values not zero")
        states[r["state"]] += int(r["records"])
    require(
        len(rows) == native["sufficient_cells"] == source["sufficient_cells"],
        "complete cell set",
    )
    require(
        sum(states.values()) == native["cohort_rows"] == source["cohort_rows"],
        "complete cohort",
    )
    for state, value in source["national_accounts"].items():
        require(value >= 0, "nonnegative source account")
        if state in list(source["national_accounts"])[4:]:
            require(states[state] == value, "complete cohort account")
    require(
        sum(source["national_accounts"].values())
        == native["national_rows"]
        == source["national_rows"],
        "complete national partition",
    )
    result = dict(
        status="PASS",
        finite_conditions=n,
        sufficient_cells=len(rows),
        cohort_rows=sum(states.values()),
        scope="Complete minimal native-bound source projection,not new acquisition,physical identity or source accuracy.",
    )
    print(json.dumps(result))
    return result


if __name__ == "__main__":
    main()
