"""Return qualified source accounts and reject unsupported individual or forecast claims."""

from pathlib import Path
import argparse, csv, json

ROOT = Path(__file__).resolve().parents[1]


def answer(request, accounts):
    if not isinstance(request, dict):
        return {
            "status": "REJECTED",
            "reason": "request must name a supported descriptive account",
        }
    if request.get("purpose") != "reported_stratum_account":
        return {
            "status": "REJECTED",
            "reason": "no safety,legal,worker eligibility or forecast inference",
        }
    if request.get("denominator") != "reported_positive_hours":
        return {
            "status": "REJECTED",
            "reason": "retain reported known positive exposure",
        }
    rows = [
        r
        for r in accounts
        if r["industry"] == request.get("industry")
        and r["size_class"] == request.get("size_class")
    ]
    if len(rows) != 1 or int(rows[0]["eligible_records"]) <= 0:
        return {
            "status": "REJECTED",
            "reason": "unique nonempty fixed stratum required",
        }
    r = rows[0]
    return dict(
        status="ACCEPTED_QUALIFIED",
        industry=r["industry"],
        size_class=r["size_class"],
        eligible_records=r["eligible_records"],
        unavailable_records=r["unavailable_records"],
        reported_cases=r["total_cases"],
        reported_hours=r["total_hours"],
        reported_rate_per100FTE=r["pooled_raw_rate"],
        future_accuracy="UNESTABLISHED",
        workplace_safety="UNESTABLISHED",
        qualification="Current submitted summary accounts,not source accuracy or representative worker risk;size uses maximum employees.",
    )


def run(out):
    with (out / "stratum_accounts.csv").open(encoding="utf-8", newline="") as f:
        accounts = list(csv.DictReader(f))
    requests = json.loads((ROOT / "data/exercise_inputs.json").read_bytes())
    result = [dict(request=r, response=answer(r, accounts)) for r in requests]
    (out / "exercise.json").write_bytes((json.dumps(result, indent=2) + "\n").encode())
    print(
        json.dumps(
            dict(
                examples=len(result),
                accepted=sum(
                    r["response"]["status"] == "ACCEPTED_QUALIFIED" for r in result
                ),
            )
        )
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, required=True)
    run(p.parse_args().out)
