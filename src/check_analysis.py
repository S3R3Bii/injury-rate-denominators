"""Reconstruct complete outputs with SQLite and direct rational algebra; no production imports."""

from pathlib import Path
from collections import defaultdict
from fractions import Fraction
from decimal import Decimal, localcontext, ROUND_HALF_EVEN
import csv, gzip, hashlib, io, json, sqlite3

ROOT = Path(__file__).resolve().parents[1]


def read(name):
    p = ROOT / name
    if name.endswith(".json"):
        return json.loads(p.read_bytes())
    data = gzip.decompress(p.read_bytes()) if name.endswith(".gz") else p.read_bytes()
    return list(csv.DictReader(io.StringIO(data.decode())))


def rounded_units(f):
    num = f.numerator * 10**12
    den = f.denominator
    q, r = divmod(num, den)
    return q + (2 * r > den or (2 * r == den and q % 2 == 1))


def decimal12(units):
    return str(units // 10**12) + "." + str(units % 10**12).zfill(12)


def main():
    n = 0

    def require(ok, label):
        nonlocal n
        assert ok, label
        n += 1

    cells = read("data/summary_cells.csv")
    eligible = [r for r in cells if r["state"] == "eligible"]
    db = sqlite3.connect(":memory:")
    db.execute(
        "CREATE TABLE cells (industry TEXT,size_class TEXT,state TEXT,k INTEGER,h TEXT,n INTEGER)"
    )
    db.executemany(
        "INSERT INTO cells VALUES (?,?,?,?,?,?)",
        (
            (
                r["industry"],
                r["size_class"],
                r["state"],
                int(r["cases"]) if r["cases"] else None,
                r["hours"] or None,
                int(r["records"]),
            )
            for r in cells
        ),
    )

    class Hours:
        def __init__(self):
            self.v = Fraction()

        def step(self, h, m):
            self.v += Fraction(h) * m if h is not None else 0

        def finalize(self):
            return str(self.v)

    db.create_aggregate("exact_hours", 2, Hours)
    k, h = db.execute(
        "SELECT SUM(k*n),exact_hours(h,n) FROM cells WHERE state='eligible'"
    ).fetchone()
    mu = Fraction(k) * 200000 / Fraction(h) if Fraction(h) > 0 else None
    proper = mu is not None and mu > 0
    accounts = read("results/stratum_accounts.csv")
    sens = read("results/sensitivity_accounts.csv")
    details = read("results/cell_sensitivities.csv.gz")
    zero = read("results/zero_count_bounds.csv.gz")
    groups = [
        (i, s)
        for i in ["31", "32", "33"]
        for s in ["20-99", "100-249", "20-249 unsplit"]
    ]
    require(
        [(r["industry"], r["size_class"]) for r in accounts] == groups,
        "complete fixed stratum grid",
    )
    strengths = [Fraction(1, 10), Fraction(1), Fraction(10)]
    require(
        [(r["industry"], r["size_class"], Fraction(r["strength"])) for r in sens]
        == [(i, s, b) for i, s in groups for b in strengths],
        "complete sensitivity grid",
    )
    require(len(details) == len(eligible) * 3, "complete cell-strength export")
    seen = set()
    agg = defaultdict(
        lambda: dict(above=0, raw=0, down=0, up=0, movement=0, weights=[])
    )
    for r in details:
        index = int(r["cell"]) - 1
        require(0 <= index < len(eligible), "valid cell identity")
        source = eligible[index]
        b = Fraction(r["strength"])
        key = (index, b)
        require(key not in seen and b in strengths, "unique fixed cell/strength")
        seen.add(key)
        require(
            all(
                r[name] == source[name]
                for name in ["industry", "size_class", "cases", "hours", "records"]
            ),
            "actual sufficient cell",
        )
        count = int(source["cases"])
        hours = Fraction(source["hours"])
        m = int(source["records"])
        t = hours / 200000
        raw = Fraction(count) / t
        post = (Fraction(count) + mu * b) / (t + b) if proper else None
        raw_flag = raw > 2 * mu if mu is not None else False
        newflag = post > 2 * mu if post is not None else None
        weight = t / (t + b)
        require(
            r["raw_rate"] == str(raw)
            and r["posterior_mean"] == (str(post) if post is not None else ""),
            "direct exact rate and posterior",
        )
        require(
            r["raw_above"] == str(int(raw_flag))
            and r["shrunk_above"] == (str(int(newflag)) if newflag is not None else ""),
            "strict exact threshold",
        )
        require(r["exposure_weight"] == str(weight), "direct exposure weight")
        units = rounded_units(abs(post - raw)) if proper else None
        require(
            r["absolute_change_rounded12"]
            == (decimal12(units) if units is not None else ""),
            "independent integer half-even movement",
        )
        a = agg[(r["industry"], r["size_class"], b)]
        if proper:
            a["above"] += m * newflag
            a["raw"] += m * raw_flag
            a["down"] += m * (raw_flag and not newflag)
            a["up"] += m * (not raw_flag and newflag)
            a["movement"] += units * m
            a["weights"].append(1 - weight)
    require(
        seen == {(i, b) for i in range(len(eligible)) for b in strengths},
        "no omitted cell/strength",
    )
    zero_seen = set()
    bounds = defaultdict(list)
    for r in zero:
        index = int(r["cell"]) - 1
        require(index not in zero_seen, "unique zero-count cell")
        zero_seen.add(index)
        source = eligible[index]
        require(int(source["cases"]) == 0, "native-bound zero numerator")
        require(
            all(
                r[k] == source[k]
                for k in ["industry", "size_class", "hours", "records"]
            ),
            "zero cell identity",
        )
        hours = Fraction(source["hours"])
        with localcontext() as context:
            context.prec = 60
            expected = (
                Decimal(20).ln()
                * Decimal(200000)
                * Decimal(hours.denominator)
                / Decimal(hours.numerator)
            )
            expected = expected.quantize(
                Decimal("0.000000000001"), rounding=ROUND_HALF_EVEN
            )
        require(
            Decimal(r["one_sided95_upper_rate"]) == expected, "independent ln20 bound"
        )
        bounds[(source["industry"], source["size_class"])].append(expected)
    require(
        zero_seen == {i for i, r in enumerate(eligible) if int(r["cases"]) == 0},
        "all zero-count cells",
    )
    for r in accounts:
        i, s = r["industry"], r["size_class"]
        group = (i, s)
        (cohort,) = db.execute(
            "SELECT SUM(n) FROM cells WHERE industry=? AND size_class=?", (i, s)
        ).fetchone()
        nr, ks, hs, z = db.execute(
            "SELECT SUM(n),SUM(k*n),exact_hours(h,n),SUM(CASE WHEN k=0 THEN n ELSE 0 END) FROM cells WHERE industry=? AND size_class=? AND state='eligible'",
            (i, s),
        ).fetchone()
        cohort = cohort or 0
        nr = nr or 0
        ks = ks or 0
        hs = Fraction(hs or 0)
        z = z or 0
        values = dict(
            cohort_records=str(cohort),
            eligible_records=str(nr),
            unavailable_records=str(cohort - nr),
            zero_case_records=str(z),
            total_cases=str(ks),
            total_hours=str(hs),
            pooled_raw_rate=str(Fraction(ks) * 200000 / hs) if hs else "",
            raw_above_twice_mean=str(agg[(i, s, strengths[0])]["raw"]),
            zero_upper_min=str(min(bounds[group])) if bounds[group] else "",
            zero_upper_max=str(max(bounds[group])) if bounds[group] else "",
        )
        require(
            all(r[field] == value for field, value in values.items()),
            "complete SQL stratum account",
        )
    for r in sens:
        b = Fraction(r["strength"])
        a = agg[(r["industry"], r["size_class"], b)]
        nr = next(
            x["eligible_records"]
            for x in accounts
            if (x["industry"], x["size_class"]) == (r["industry"], r["size_class"])
        )
        require(r["records"] == nr, "sensitivity denominator")
        require(int(r["raw_above"]) == a["raw"], "raw strict boundary count")
        if proper:
            require(
                all(
                    int(r[field]) == a[name]
                    for field, name in [
                        ("shrunk_above", "above"),
                        ("high_to_low", "down"),
                        ("low_to_high", "up"),
                    ]
                ),
                "all switch directions",
            )
            require(
                Decimal(r["absolute_rate_movement_sum_rounded12"]) * 10**12
                == a["movement"],
                "exact sum of rounded cell movement",
            )
            require(
                r["prior_weight_min"]
                == (str(min(a["weights"])) if a["weights"] else "")
                and r["prior_weight_max"]
                == (str(max(a["weights"])) if a["weights"] else ""),
                "complete prior-weight range",
            )
            require(
                a["raw"] - a["down"] + a["up"] == a["above"],
                "switch accounting identity",
            )
    summary = read("results/summary.json")
    source = read("data/source_accounts.json")
    expected = dict(
        national_rows=source["national_rows"],
        cohort_rows=source["cohort_rows"],
        eligible_records=sum(int(r["records"]) for r in eligible),
        eligible_source_cells=len(eligible),
        nonpositive_exposure_records=source["national_accounts"][
            "nonpositive_exposure"
        ],
        total_cases=k,
        total_hours=str(Fraction(h)),
        pooled_rate=str(mu) if mu is not None else None,
        zero_case_records=sum(
            int(r["records"]) for r in eligible if int(r["cases"]) == 0
        ),
        raw_above_twice_pooled_mean=sum(
            int(r["raw_above_twice_mean"]) for r in accounts
        ),
        strata=9,
        sensitivity_cases=27,
        cell_strength_cases=len(eligible) * 3,
        original_year_held_out_forecast="UNEXECUTED",
    )
    for field, value in expected.items():
        require(summary[field] == value, ("complete summary", field))
    for b in strengths:
        for field, metric in [("high_to_low", "down"), ("low_to_high", "up")]:
            require(
                summary[field][str(b)]
                == (
                    sum(a[metric] for key, a in agg.items() if key[2] == b)
                    if proper
                    else None
                ),
                "complete direction summary",
            )
    examples = read("results/exercise.json")
    requests = read("data/exercise_inputs.json")
    require(
        [r["request"] for r in examples] == requests and len(examples) == 7,
        "all fixed requests",
    )
    for index, r in enumerate(examples):
        response = r["response"]
        if index < 2:
            account = next(
                a
                for a in accounts
                if a["industry"] == r["request"]["industry"]
                and a["size_class"] == r["request"]["size_class"]
            )
            require(
                response["status"] == "ACCEPTED_QUALIFIED", "supported current account"
            )
            require(
                response["reported_cases"] == account["total_cases"]
                and response["reported_hours"] == account["total_hours"]
                and response["reported_rate_per100FTE"] == account["pooled_raw_rate"],
                "actual qualified numerator/denominator/rate",
            )
            require(
                response["future_accuracy"]
                == response["workplace_safety"]
                == "UNESTABLISHED",
                "explicit unknowns",
            )
        else:
            require(response["status"] == "REJECTED", "unsupported claim rejected")
    receipt = dict(
        status="PASS",
        finite_conditions=n,
        strata=9,
        sensitivity_cases=27,
        complete_cell_strength_cases=len(details),
        zero_count_cells=len(zero),
        examples=7,
        method="Independent SQLite weighted source aggregates,direct Fraction algebra,integer half-even rounding and ln20 bounds;no production imports",
        scope="Finite descriptive model/threshold sensitivity and complete source counts;not empirical interval calibration,future accuracy or safety validity.",
    )
    (ROOT / "results/independent_check.json").write_bytes(
        (json.dumps(receipt, indent=2) + "\n").encode()
    )
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
