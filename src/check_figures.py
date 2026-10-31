"""Independently bind all actual SVG bars to complete reported-rate source results."""

from pathlib import Path
from fractions import Fraction
import csv, hashlib, json, re, xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def read(name):
    with (ROOT / name).open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def main():
    n = 0
    coordinates = 0

    def require(ok, label):
        nonlocal n
        assert ok, label
        n += 1

    accounts = read("results/stratum_accounts.csv")
    sens = read("results/sensitivity_accounts.csv")
    diag = read("results/exposure_concentration.csv")
    expected = {}

    def key(file, field, query):
        return (file, field, tuple(sorted(query.items())))

    for i, r in enumerate(diag):
        for field, operation in [
            ("share_of_hours", "percent"),
            ("conditional_remaining_rate", "value"),
        ]:
            value = float(Fraction(r[field])) * (100 if operation == "percent" else 1)
            expected[
                key(
                    "results/exposure_concentration.csv",
                    field,
                    {"top_records": r["top_records"]},
                )
            ] = (value, "vertical", i, 0.6, operation)
    for i, r in enumerate(accounts):
        q = dict(industry=r["industry"], size_class=r["size_class"])
        for field in [
            "raw_above_twice_mean",
            "eligible_records",
            "unavailable_records",
        ]:
            expected[key("results/stratum_accounts.csv", field, q)] = (
                float(r[field]),
                "horizontal",
                i,
                0.6,
                "value",
            )
        for j, b in enumerate(["1/10", "1", "10"]):
            row = next(
                x
                for x in sens
                if all(x[k] == v for k, v in q.items()) and x["strength"] == b
            )
            expected[
                key(
                    "results/sensitivity_accounts.csv",
                    "high_to_low",
                    dict(q, strength=b),
                )
            ] = (
                float(row["high_to_low"]),
                "horizontal",
                i + (j - 1) * 0.24,
                0.22,
                "value",
            )
    figures = json.loads((ROOT / "figures/manifest.json").read_bytes())
    seen = set()
    bindings = set()
    require(len(figures) == 3, "three declared figures")
    for fig in figures:
        tree = ET.fromstring((ROOT / "figures" / (fig["name"] + ".svg")).read_bytes())
        groups = {r.attrib.get("id"): r for r in tree.iter() if r.tag.endswith("g")}
        texts = [
            "".join(r.itertext()).strip() for r in tree.iter() if r.tag.endswith("text")
        ]
        for ext, digest in fig["asset_sha256"].items():
            require(
                hashlib.sha256(
                    (ROOT / "figures" / (fig["name"] + "." + ext)).read_bytes()
                ).hexdigest()
                == digest,
                "current asset SHA256",
            )
        for item in fig["artists"]:
            gid = item["gid"]
            require(gid not in seen, "unique SVG source bar")
            seen.add(gid)
            binding = key(item["file"], item["field"], item["query"])
            require(
                binding in expected and binding not in bindings,
                "complete unique source binding",
            )
            bindings.add(binding)
            value, orientation, position, thickness, operation = expected[binding]
            require(abs(value - item["value"]) < 1e-12, "independent source value")
            require(
                item["orientation"] == orientation
                and abs(item["position"] - position) < 1e-12
                and item["thickness"] == thickness
                and item["operation"] == operation,
                "declared actual source position and scale",
            )
            if "label" in item:
                require(item["label"] in texts, "actual SVG numeric label")
            paths = [x for x in groups[gid].iter() if x.tag.endswith("path")]
            require(len(paths) == 1, "actual bar path")
            numbers = list(
                map(
                    float,
                    re.findall(
                        r"[-+]?(?:\d*\.)?\d+(?:[eE][-+]?\d+)?", paths[0].attrib["d"]
                    ),
                )
            )
            require(len(numbers) == 8, "four source-bar corners")
            xs = numbers[::2]
            ys = numbers[1::2]
            a = item["axis_points"]
            lo, hi = a["xlim"]
            bottom, top = a["ylim"]
            x = lambda v: a["left"] + (v - lo) / (hi - lo) * a["width"]
            y = lambda v: a["top"] + (top - v) / (top - bottom) * a["height"]
            if item["orientation"] == "vertical":
                expected_x = [
                    x(item["position"] - item["thickness"] / 2),
                    x(item["position"] + item["thickness"] / 2),
                ]
                expected_y = [y(0), y(float(value))]
            else:
                expected_x = [x(0), x(float(value))]
                expected_y = [
                    y(item["position"] - item["thickness"] / 2),
                    y(item["position"] + item["thickness"] / 2),
                ]
            for actual, target in [
                (min(xs), min(expected_x)),
                (max(xs), max(expected_x)),
                (min(ys), min(expected_y)),
                (max(ys), max(expected_y)),
            ]:
                require(abs(actual - target) < 0.02, "actual SVG source geometry")
                coordinates += 1
        if fig["name"] in ["smoothing_sensitivity", "source_denominators"]:
            require(
                all(r["industry"] + " | " + r["size_class"] in texts for r in accounts),
                "all fixed strata visibly labeled",
            )
    require(bindings == set(expected) and len(seen) == 62, "all62 complete source bars")
    receipt = dict(
        status="PASS",
        finite_conditions=n,
        source_bound_artists=len(seen),
        svg_coordinate_conditions=coordinates,
        asset_hashes=9,
        scope="Actual62 SVG bars,complete source values and positions,all fixed strata,retrospective top-k cases and asset hashes;visual review separate,no safety validity or accessibility certification.",
    )
    (ROOT / "figures/verification.json").write_bytes(
        (json.dumps(receipt, indent=2) + "\n").encode()
    )
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
