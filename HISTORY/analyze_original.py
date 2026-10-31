"""Export every fixed stratum, strength and eligible sufficient-cell sensitivity."""

from pathlib import Path
from collections import defaultdict
from decimal import Decimal
from fractions import Fraction
import argparse, csv, gzip, io, json
from metrics import rate, posterior, fixed12, zero_upper, STRENGTHS

ROOT = Path(__file__).resolve().parents[1]
SIZES = ["20-99", "100-249", "20-249 unsplit"]


def write_csv(path, rows, fields):
    out = io.StringIO(newline="")
    w = csv.DictWriter(out, fieldnames=fields, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    data = out.getvalue().encode()
    path.write_bytes(
        gzip.compress(data, mtime=0) if path.name.endswith(".gz") else data
    )


def run(out):
    assert not out.exists()
    out.mkdir(parents=True)
    with (ROOT / "data/summary_cells.csv").open(encoding="utf-8", newline="") as f:
        cells = list(csv.DictReader(f))
    eligible = [r for r in cells if r["state"] == "eligible"]
    total_cases = sum(int(r["cases"]) * int(r["records"]) for r in eligible)
    total_hours = sum(
        (Fraction(r["hours"]) * int(r["records"]) for r in eligible), Fraction()
    )
    mean = rate(total_cases, total_hours) if total_hours > 0 else None
    proper = mean is not None and mean > 0
    accounts = []
    sensitivity = []
    details = []
    zeros = []
    fields = [
        "industry",
        "size_class",
        "cohort_records",
        "eligible_records",
        "unavailable_records",
        "zero_case_records",
        "total_cases",
        "total_hours",
        "pooled_raw_rate",
        "raw_above_twice_mean",
        "zero_upper_min",
        "zero_upper_max",
    ]
    sf = [
        "industry",
        "size_class",
        "strength",
        "records",
        "raw_above",
        "shrunk_above",
        "high_to_low",
        "low_to_high",
        "absolute_rate_movement_sum_rounded12",
        "prior_weight_min",
        "prior_weight_max",
    ]
    df = [
        "cell",
        "industry",
        "size_class",
        "cases",
        "hours",
        "records",
        "strength",
        "raw_rate",
        "posterior_mean",
        "raw_above",
        "shrunk_above",
        "exposure_weight",
        "absolute_change_rounded12",
    ]
    zf = [
        "cell",
        "industry",
        "size_class",
        "hours",
        "records",
        "one_sided95_upper_rate",
    ]
    for industry in ["31", "32", "33"]:
        for size in SIZES:
            group = [
                r
                for r in cells
                if r["industry"] == industry and r["size_class"] == size
            ]
            valid = [r for r in group if r["state"] == "eligible"]
            nr = sum(int(r["records"]) for r in valid)
            cohort = sum(int(r["records"]) for r in group)
            k = sum(int(r["cases"]) * int(r["records"]) for r in valid)
            h = sum(
                (Fraction(r["hours"]) * int(r["records"]) for r in valid), Fraction()
            )
            zero = [r for r in valid if int(r["cases"]) == 0]
            bounds = [Decimal(zero_upper(r["hours"])) for r in zero]
            rawabove = sum(
                int(r["records"])
                for r in valid
                if mean is not None and rate(r["cases"], r["hours"]) > 2 * mean
            )
            accounts.append(
                dict(
                    zip(
                        fields,
                        [
                            industry,
                            size,
                            cohort,
                            nr,
                            cohort - nr,
                            sum(int(r["records"]) for r in zero),
                            k,
                            str(h),
                            str(rate(k, h)) if h else "",
                            rawabove,
                            str(min(bounds)) if bounds else "",
                            str(max(bounds)) if bounds else "",
                        ],
                    )
                )
            )
            for b in STRENGTHS:
                above = down = up = 0
                movement = 0
                prior_weights = []
                for i, r in enumerate(eligible):
                    if r["industry"] != industry or r["size_class"] != size:
                        continue
                    n = int(r["records"])
                    raw = rate(r["cases"], r["hours"])
                    post = (
                        posterior(r["cases"], r["hours"], mean, b) if proper else None
                    )
                    flag = raw > 2 * mean if mean is not None else False
                    newflag = post > 2 * mean if post is not None else None
                    weight = Fraction(r["hours"]) / (Fraction(r["hours"]) + 200000 * b)
                    change = fixed12(abs(post - raw)) if post is not None else ""
                    if proper:
                        above += n * newflag
                        down += n * (flag and not newflag)
                        up += n * (not flag and newflag)
                        movement += int(Decimal(change) * 10**12) * n
                        prior_weights.append(1 - weight)
                    details.append(
                        dict(
                            zip(
                                df,
                                [
                                    i + 1,
                                    industry,
                                    size,
                                    r["cases"],
                                    r["hours"],
                                    n,
                                    str(b),
                                    str(raw),
                                    str(post) if post is not None else "",
                                    int(flag),
                                    int(newflag) if newflag is not None else "",
                                    str(weight),
                                    change,
                                ],
                            )
                        )
                    )
                    if b == STRENGTHS[0] and int(r["cases"]) == 0:
                        zeros.append(
                            dict(
                                zip(
                                    zf,
                                    [
                                        i + 1,
                                        industry,
                                        size,
                                        r["hours"],
                                        n,
                                        zero_upper(r["hours"]),
                                    ],
                                )
                            )
                        )
                sensitivity.append(
                    dict(
                        zip(
                            sf,
                            [
                                industry,
                                size,
                                str(b),
                                nr,
                                rawabove,
                                above if proper else "",
                                down if proper else "",
                                up if proper else "",
                                (
                                    (
                                        str(movement // 10**12)
                                        + "."
                                        + str(movement % 10**12).zfill(12)
                                    )
                                    if proper
                                    else ""
                                ),
                                str(min(prior_weights)) if prior_weights else "",
                                str(max(prior_weights)) if prior_weights else "",
                            ],
                        )
                    )
                )
    write_csv(out / "stratum_accounts.csv", accounts, fields)
    write_csv(out / "sensitivity_accounts.csv", sensitivity, sf)
    write_csv(out / "cell_sensitivities.csv.gz", details, df)
    write_csv(out / "zero_count_bounds.csv.gz", zeros, zf)
    source = json.loads((ROOT / "data/source_accounts.json").read_bytes())
    summary = dict(
        national_rows=source["national_rows"],
        cohort_rows=source["cohort_rows"],
        eligible_records=sum(int(r["records"]) for r in eligible),
        eligible_source_cells=len(eligible),
        nonpositive_exposure_records=source["national_accounts"][
            "nonpositive_exposure"
        ],
        total_cases=total_cases,
        total_hours=str(total_hours),
        pooled_rate=str(mean) if mean is not None else None,
        zero_case_records=sum(
            int(r["records"]) for r in eligible if int(r["cases"]) == 0
        ),
        raw_above_twice_pooled_mean=sum(
            int(r["records"])
            for r in eligible
            if mean is not None and rate(r["cases"], r["hours"]) > 2 * mean
        ),
        strata=len(accounts),
        sensitivity_cases=len(sensitivity),
        cell_strength_cases=len(details),
        working_model=(
            "AVAILABLE_DESCRIPTIVE_ONLY"
            if proper
            else "UNAVAILABLE_ZERO_OR_MISSING_POOLED_MEAN"
        ),
        strengths=[str(b) for b in STRENGTHS],
        high_to_low={
            str(b): (
                sum(
                    int(r["high_to_low"])
                    for r in sensitivity
                    if r["strength"] == str(b)
                )
                if proper
                else None
            )
            for b in STRENGTHS
        },
        low_to_high={
            str(b): (
                sum(
                    int(r["low_to_high"])
                    for r in sensitivity
                    if r["strength"] == str(b)
                )
                if proper
                else None
            )
            for b in STRENGTHS
        },
        original_year_held_out_forecast="UNEXECUTED",
        qualification="Same-cohort-centered descriptive Gamma-Poisson sensitivity;authored strengths and two-times boundary;no selected winner,safety ranking,prediction-time features or future-risk accuracy.",
    )
    (out / "summary.json").write_bytes((json.dumps(summary, indent=2) + "\n").encode())
    print(json.dumps(summary))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, required=True)
    run(p.parse_args().out)
