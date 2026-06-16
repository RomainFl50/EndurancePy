"""Plot lap-time evolution over a session, coloured by class.

Requires the plotting extra (``pip install endurancepy[plot]``). Run with::

    python examples/plot_lap_evolution.py path/to/23_Analysis_Race.CSV out.png

Each clean (green-flag, non-pit) lap is plotted as lap time vs lap number, with
one colour per class — a quick way to see pace, traffic and degradation.
"""

from __future__ import annotations

import sys
from pathlib import Path

import endurancepy as ep
from endurancepy import plotting


def plot(analysis_csv: str | Path, output: str | Path = "lap_evolution.png") -> Path:
    """Render the lap-time evolution scatter and save it to ``output``."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    laps = ep.read_analysis(analysis_csv)
    clean = laps.pick_wo_box().pick_track_status("GF")

    fig, ax = plt.subplots(figsize=(9, 5))
    seen: set[str] = set()
    for class_name in sorted(laps["Class"].dropna().unique()):
        color = plotting.get_class_color(class_name)
        for _, car_laps in clean.pick_classes(class_name).groupby("CarNumber"):
            seconds = car_laps["LapTime"].dt.total_seconds()
            ax.plot(
                car_laps["LapNumber"],
                seconds,
                ".-",
                color=color,
                alpha=0.7,
                label=class_name if class_name not in seen else None,
            )
            seen.add(class_name)

    ax.set_xlabel("Lap number")
    ax.set_ylabel("Lap time (s)")
    ax.set_title("Lap-time evolution by class")
    ax.legend()

    output = Path(output)
    fig.savefig(output, dpi=120, bbox_inches="tight")
    plt.close(fig)
    return output


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(
            "Usage: python examples/plot_lap_evolution.py <Analysis.CSV> [out.png]"
        )
    out = sys.argv[2] if len(sys.argv) > 2 else "lap_evolution.png"
    print("Saved", plot(sys.argv[1], out))
