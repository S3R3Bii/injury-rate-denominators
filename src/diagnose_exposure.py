"""Retrospective exposure-concentration accounting; no source cleaning or model reselection."""

from pathlib import Path
from fractions import Fraction
import csv, json

ROOT = Path(__file__).resolve().parents[1]


def main():
    with (ROOT / "data/summary_cells.csv").open(encoding="utf-8", newline="") as f:
        cells = [r for r in csv.DictReader(f) if r["state"] == "eligible"]
    rows = sorted(
        cells,
        key=lambda r: (
            -Fraction(r["hours"]),
            r["industry"],
            r["size_class"],
            int(r["cases"]),
        ),
    )
    h = sum((Fraction(r["hours"]) * int(r["records"]) for r in rows), Fraction())
    k = sum(int(r["cases"]) * int(r["records"]) for r in rows)
    n = sum(int(r["records"]) for r in rows)
    result = []
    for top in [1, 5, 10, 100]:
        remaining = top
        removed_h = Fraction()
        removed_k = 0
        for r in rows:
            take = min(remaining, int(r["records"]))
            removed_h += take * Fraction(r["hours"])
            removed_k += take * int(r["cases"])
            remaining -= take
            if remaining == 0:
                break
        assert remaining == 0 and h > removed_h
        result.append(
            dict(
                top_records=top,
                total_records=n,
                total_hours=str(h),
                top_hours=str(removed_h),
                share_of_hours=str(removed_h / h),
                top_cases=removed_k,
                remaining_cases=k - removed_k,
                remaining_hours=str(h - removed_h),
                conditional_remaining_rate=str(
                    Fraction(k - removed_k) * 200000 / (h - removed_h)
                ),
            )
        )
    fields = list(result[0])
    with (ROOT / "results/exposure_concentration.csv").open(
        "w", encoding="utf-8", newline=""
    ) as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(result)
    receipt = dict(
        scope="RETROSPECTIVE_DIAGNOSTIC",
        trigger="After the frozen comparison exposed a361383028589-hour total and a dominant industry32/unsplit-size stratum.",
        source_changed=False,
        model_or_strength_selected=False,
        full_cohort_rate=str(Fraction(k) * 200000 / h),
        maximum_single_record_hours=str(Fraction(rows[0]["hours"])),
        qualification="All four top-k cases retained.No source correction,cleaned dataset,empirical prior validation or representative worker risk is claimed.Conditional remaining rates are labeled retrospective accounting diagnostics,not replacement estimates.",
    )
    (ROOT / "results/exposure_diagnostic.json").write_bytes(
        (json.dumps(receipt, indent=2) + "\n").encode()
    )
    print(json.dumps(receipt))
    print(json.dumps(result))


if __name__ == "__main__":
    main()
