"""Plot green-flag pace by class from a local Analysis CSV.

Requires the plotting extra (``pip install endurancepy[plot]``). Run with::

    python examples/plot_pace_by_class.py path/to/23_Analysis_Race.CSV out.png

Produces a box plot of clean (green-flag, non-pit) lap times per class, coloured
with EndurancePy's class palette.
"""

from __future__ import annotations

import sys
from pathlib import Path

import endurancepy as ep
from endurancepy import plotting


def plot(analysis_csv: str | Path, output: str | Path = "pace_by_class.png") -> Path:
    """Render the pace-by-class box plot and save it to ``output``."""
    import matplotlib

    matplotlib.use("Agg")  # headless backend; safe in scripts/CI
    import matplotlib.pyplot as plt

    laps = ep.read_analysis(analysis_csv)
    clean = laps.pick_wo_box().pick_track_status("GF")

    data, labels, colors = [], [], []
    for class_name in sorted(laps["Class"].dropna().unique()):
        seconds = clean.pick_classes(class_name)["LapTime"].dropna().dt.total_seconds()
        if len(seconds):
            data.append(seconds.to_numpy())
            labels.append(class_name)
            colors.append(plotting.get_class_color(class_name))

    fig, ax = plt.subplots(figsize=(8, 5))
    box = ax.boxplot(data, patch_artist=True)
    for patch, color in zip(box["boxes"], colors, strict=False):
        patch.set_facecolor(color)
    ax.set_xticks(range(1, len(labels) + 1))
    ax.set_xticklabels(labels)
    ax.set_ylabel("Lap time (s)")
    ax.set_title("Green-flag pace by class")

    output = Path(output)
    fig.savefig(output, dpi=120, bbox_inches="tight")
    plt.close(fig)
    return output


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(
            "Usage: python examples/plot_pace_by_class.py <Analysis.CSV> [out.png]"
        )
    out = sys.argv[2] if len(sys.argv) > 2 else "pace_by_class.png"
    print("Saved", plot(sys.argv[1], out))
