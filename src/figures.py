"""Render complete source accounts and explicitly retrospective exposure diagnostics."""

from pathlib import Path
from fractions import Fraction
import csv, hashlib, json
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]


def read(name):
    with (ROOT / name).open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def main():
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "svg.fonttype": "none",
            "svg.hashsalt": "injury-rate-denominators",
        }
    )
    folder = ROOT / "figures"
    folder.mkdir(exist_ok=True)
    manifest = []
    palette = ["#177f83", "#d18a22", "#5d59b1"]

    def bar(
        ax,
        row,
        file,
        field,
        query,
        position,
        thickness,
        orientation="horizontal",
        operation="value",
        color="#177f83",
        label_format=",.0f",
    ):
        value = float(Fraction(row[field])) * (100 if operation == "percent" else 1)
        patch = (
            ax.barh(position, value, height=thickness, color=color)[0]
            if orientation == "horizontal"
            else ax.bar(position, value, width=thickness, color=color)[0]
        )
        gid = "source-" + str(len(manifest)) + "-" + str(len(items))
        patch.set_gid(gid)
        label = format(value, label_format) + ("%" if operation == "percent" else "")
        if orientation == "horizontal":
            ax.annotate(
                label,
                (value, position),
                xytext=(4, 0),
                textcoords="offset points",
                va="center",
                fontsize=8,
            )
        else:
            ax.annotate(
                label,
                (position, value),
                xytext=(0, 4),
                textcoords="offset points",
                ha="center",
                fontsize=9,
            )
        items.append(
            (
                dict(
                    gid=gid,
                    file=file,
                    field=field,
                    query=query,
                    operation=operation,
                    value=value,
                    position=position,
                    thickness=thickness,
                    orientation=orientation,
                    label=label,
                ),
                ax,
            )
        )

    def finish(fig, name):
        fig.canvas.draw()
        width, height = fig.get_size_inches() * 72
        for item, ax in items:
            box = ax.get_position()
            item["axis_points"] = dict(
                left=float(box.x0 * width),
                top=float((1 - box.y1) * height),
                width=float(box.width * width),
                height=float(box.height * height),
                xlim=list(map(float, ax.get_xlim())),
                ylim=list(map(float, ax.get_ylim())),
            )
        for ext in ["png", "svg", "pdf"]:
            metadata = (
                {"Date": None}
                if ext == "svg"
                else {"CreationDate": None, "ModDate": None} if ext == "pdf" else None
            )
            fig.savefig(
                folder / (name + "." + ext),
                dpi=160,
                facecolor="white",
                metadata=metadata,
            )
        p = folder / (name + ".svg")
        p.write_bytes(
            (
                "\n".join(
                    x.rstrip() for x in p.read_text(encoding="utf-8").splitlines()
                )
                + "\n"
            ).encode()
        )
        manifest.append(
            dict(
                name=name,
                artists=[a for a, ax in items],
                asset_sha256={
                    ext: hashlib.sha256(
                        (folder / (name + "." + ext)).read_bytes()
                    ).hexdigest()
                    for ext in ["png", "svg", "pdf"]
                },
            )
        )
        plt.close(fig)

    diag = read("results/exposure_concentration.csv")
    accounts = read("results/stratum_accounts.csv")
    sens = read("results/sensitivity_accounts.csv")
    fig, axes = plt.subplots(1, 2, figsize=(12, 6))
    fig.subplots_adjust(left=0.08, right=0.96, top=0.73, bottom=0.19, wspace=0.36)
    fig.suptitle(
        "Five of 46,511 records carry most reported hours",
        x=0.08,
        ha="left",
        y=0.97,
        fontsize=16,
    )
    fig.text(
        0.08,
        0.88,
        "Retrospective exposure audit: all four top-k cases retained; full source and frozen estimates unchanged",
        fontsize=10,
    )
    items = []
    for panel, (field, operation, title, ylabel) in enumerate(
        [
            (
                "share_of_hours",
                "percent",
                "Share held by the top records",
                "Percent of eligible reported hours",
            ),
            (
                "conditional_remaining_rate",
                "value",
                "Rate among the remaining records",
                "Reported cases per 100 FTE worker-years",
            ),
        ]
    ):
        ax = axes[panel]
        for i, row in enumerate(diag):
            bar(
                ax,
                row,
                "results/exposure_concentration.csv",
                field,
                dict(top_records=row["top_records"]),
                i,
                0.6,
                "vertical",
                operation,
                palette[panel],
                ".2f" if panel == 0 else ".3f",
            )
        ax.set_xticks(range(4), [r["top_records"] for r in diag])
        ax.set_xlabel("Number of highest-hour records")
        ax.set_ylabel(ylabel)
        ax.set_title(title, loc="left", fontsize=11, pad=18)
        ax.set_ylim(
            0,
            110 if panel == 0 else max(float(Fraction(r[field])) for r in diag) * 1.23,
        )
        ax.grid(axis="y", alpha=0.18)
        ax.set_axisbelow(True)
    full = float(
        Fraction(
            json.loads((ROOT / "results/summary.json").read_bytes())["pooled_rate"]
        )
    )
    axes[1].axhline(
        full,
        color="#555555",
        linestyle="--",
        linewidth=1,
        label="Full cohort: " + format(full, ".3f"),
    )
    axes[1].legend(frameon=False, fontsize=9, loc="upper left")
    fig.text(
        0.08,
        0.04,
        "Conditional rates are accounting diagnostics, not corrected data or replacement population estimates.",
        fontsize=9,
    )
    finish(fig, "exposure_concentration")
    labels = [r["industry"] + " | " + r["size_class"] for r in accounts]
    fig, axes = plt.subplots(1, 2, figsize=(12, 7))
    fig.subplots_adjust(left=0.17, right=0.95, top=0.76, bottom=0.13, wspace=0.5)
    fig.suptitle(
        "Declared smoothing assumptions change a reported-rate label",
        x=0.06,
        ha="left",
        y=0.98,
        fontsize=15,
    )
    fig.text(
        0.06,
        0.91,
        "Authored boundary: rate > twice the same-cohort pooled rate. No safety meaning or selected prior strength.",
        fontsize=10,
    )
    items = []
    for i, row in enumerate(accounts):
        q = dict(industry=row["industry"], size_class=row["size_class"])
        bar(
            axes[0],
            row,
            "results/stratum_accounts.csv",
            "raw_above_twice_mean",
            q,
            i,
            0.6,
        )
        for j, b in enumerate(["1/10", "1", "10"]):
            r = next(
                x
                for x in sens
                if all(x[k] == v for k, v in q.items()) and x["strength"] == b
            )
            bar(
                axes[1],
                r,
                "results/sensitivity_accounts.csv",
                "high_to_low",
                dict(q, strength=b),
                i + (j - 1) * 0.24,
                0.22,
                color=palette[j],
            )
    for ax in axes:
        ax.set_yticks(range(9), labels)
        ax.invert_yaxis()
        ax.grid(axis="x", alpha=0.18)
        ax.set_axisbelow(True)
    axes[0].set_xlim(0, max(int(r["raw_above_twice_mean"]) for r in accounts) * 1.22)
    axes[0].set_xlabel("Eligible records above the raw boundary")
    axes[0].set_title("All nine fixed strata", loc="left", pad=18, fontsize=11)
    axes[1].set_xlim(0, max(int(r["high_to_low"]) for r in sens) * 1.4)
    axes[1].set_xlabel("Records moving from above to at/below")
    axes[1].set_title(
        "All three declared prior exposures", loc="left", pad=18, fontsize=11
    )
    from matplotlib.patches import Patch

    axes[1].legend(
        handles=[
            Patch(color=c, label="b=" + b) for c, b in zip(palette, ["0.1", "1", "10"])
        ],
        frameon=False,
        ncol=3,
        loc="upper right",
        bbox_to_anchor=(1, 1),
        fontsize=9,
    )
    fig.text(
        0.06,
        0.025,
        "Size uses reported maximum employment. Broad NAICS prefixes mix source code versions; no employer ranks.",
        fontsize=9,
    )
    finish(fig, "smoothing_sensitivity")
    fig, axes = plt.subplots(1, 2, figsize=(12, 7))
    fig.subplots_adjust(left=0.17, right=0.95, top=0.77, bottom=0.13, wspace=0.5)
    fig.suptitle(
        "Nonpositive hours remain outside the rate denominator",
        x=0.06,
        ha="left",
        y=0.98,
        fontsize=16,
    )
    fig.text(
        0.06,
        0.91,
        "Complete fixed manufacturing cohort: 46,530 source records, 46,511 eligible and 19 with nonpositive hours",
        fontsize=10,
    )
    items = []
    for panel, field in enumerate(["eligible_records", "unavailable_records"]):
        ax = axes[panel]
        for i, row in enumerate(accounts):
            bar(
                ax,
                row,
                "results/stratum_accounts.csv",
                field,
                dict(industry=row["industry"], size_class=row["size_class"]),
                i,
                0.6,
                color=palette[panel],
            )
        ax.set_yticks(range(9), labels)
        ax.invert_yaxis()
        ax.grid(axis="x", alpha=0.18)
        ax.set_axisbelow(True)
        ax.set_xlim(0, max(int(r[field]) for r in accounts) * 1.25)
        ax.set_xlabel("Current source-record count")
    axes[0].set_title(
        "Known count and positive reported hours", loc="left", pad=18, fontsize=11
    )
    axes[1].set_title(
        "Nonpositive reported hours, retained explicitly",
        loc="left",
        pad=18,
        fontsize=11,
    )
    fig.text(
        0.06,
        0.025,
        "Source: OSHA ITA 2025 Summary Data. No unknown value is filled with zero; source accuracy is not established.",
        fontsize=9,
    )
    finish(fig, "source_denominators")
    (folder / "manifest.json").write_bytes(
        (json.dumps(manifest, indent=2) + "\n").encode()
    )
    print("THREE_SOURCE_BOUND_FIGURES", sum(len(r["artists"]) for r in manifest))


if __name__ == "__main__":
    main()
