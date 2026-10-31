"""Independently verify retrospective top-k exposure accounting with SQLite record expansion."""

from pathlib import Path
from fractions import Fraction
import csv, hashlib, json, sqlite3

ROOT = Path(__file__).resolve().parents[1]


def main():
    db = sqlite3.connect(":memory:")
    db.execute("CREATE TABLE records (hours INTEGER,cases INTEGER)")
    with (ROOT / "data/summary_cells.csv").open(encoding="utf-8", newline="") as f:
        cells = [r for r in csv.DictReader(f) if r["state"] == "eligible"]
    # Integer-hour eligibility is checked, not assumed from the source dictionary.
    assert all(Fraction(r["hours"]).denominator == 1 for r in cells)
    db.executemany(
        "INSERT INTO records VALUES (?,?)",
        (
            (int(r["hours"]), int(r["cases"]))
            for r in cells
            for _ in range(int(r["records"]))
        ),
    )
    total, n, k = db.execute(
        "SELECT SUM(hours),COUNT(*),SUM(cases) FROM records"
    ).fetchone()
    with (ROOT / "results/exposure_concentration.csv").open(
        encoding="utf-8", newline=""
    ) as f:
        rows = list(csv.DictReader(f))
    count = 1
    assert [int(r["top_records"]) for r in rows] == [1, 5, 10, 100]
    for r in rows:
        top = int(r["top_records"])
        values = db.execute(
            "SELECT hours,cases FROM records ORDER BY hours DESC LIMIT ?", (top,)
        ).fetchall()
        hours = sum(h for h, c in values)
        cases = sum(c for h, c in values)
        expected = dict(
            top_records=str(top),
            total_records=str(n),
            total_hours=str(total),
            top_hours=str(hours),
            share_of_hours=str(Fraction(hours, total)),
            top_cases=str(cases),
            remaining_cases=str(k - cases),
            remaining_hours=str(total - hours),
            conditional_remaining_rate=str(
                Fraction((k - cases) * 200000, total - hours)
            ),
        )
        assert r == expected
        count += len(expected)
    note = json.loads((ROOT / "results/exposure_diagnostic.json").read_bytes())
    assert (
        note["scope"] == "RETROSPECTIVE_DIAGNOSTIC"
        and note["source_changed"] is False
        and note["model_or_strength_selected"] is False
    )
    count += 1
    assert note["full_cohort_rate"] == str(Fraction(k * 200000, total)) and note[
        "maximum_single_record_hours"
    ] == str(db.execute("SELECT MAX(hours) FROM records").fetchone()[0])
    count += 2
    receipt = dict(
        status="PASS",
        finite_conditions=count,
        complete_top_k_cases=4,
        expanded_records=n,
        method="Independent SQLite record expansion and exact Fraction accounting,no production imports",
        diagnostic_sha256={
            name: hashlib.sha256((ROOT / "results" / name).read_bytes()).hexdigest()
            for name in ["exposure_concentration.csv", "exposure_diagnostic.json"]
        },
        scope="Retrospective exposure concentration;does not validate an alternative cleaned source or forecasting model.",
    )
    (ROOT / "results/diagnostic_verification.json").write_bytes(
        (json.dumps(receipt, indent=2) + "\n").encode()
    )
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
