"""Plot green-flag pace by class for a real session (loaded over the network).

Requires the plotting extra (``pip install endurancepy[plot]``). Run with::

    python examples/plot_pace_by_class.py

Box plot of clean (green-flag, non-pit) lap times per class, coloured with
EndurancePy's class palette. No CSV path needed.
"""

from __future__ import annotations

from pathlib import Path

import endurancepy as ep
from endurancepy import plotting
from endurancepy.core import Session


def plot(session: Session, output: str | Path = "pace_by_class.png") -> Path:
    """Render the pace-by-class box plot for a loaded session."""
    import matplotlib

    matplotlib.use("Agg")  # headless backend; safe in scripts/CI
    import matplotlib.pyplot as plt

    laps = session.laps
    clean = laps.pick_wo_box()
    green = clean.pick_track_status("GF")
    # Older seasons (e.g. 2018-2019) have no per-lap flag column, so green-flag
    # filtering would drop every lap; fall back to all non-pit laps in that case.
    clean = green if len(green) else clean

    data, labels, colors = [], [], []
    for class_name in sorted(laps["Class"].dropna().unique()):
        # Representative pace: laps within 107% of the class best (drops the
        # safety-car / heavy-traffic laps that would otherwise skew the box).
        cls = clean.pick_classes(class_name).pick_quicklaps()
        seconds = cls["LapTime"].dropna().dt.total_seconds()
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
    ax.set_title("Race pace by class (laps within 107% of class best)")

    output = Path(output)
    fig.savefig(output, dpi=120, bbox_inches="tight")
    plt.close(fig)
    return output


def main() -> None:
    ep.set_log_level("INFO")  # show discovery/download progress on stderr
    Path("./endurancepy-cache").mkdir(exist_ok=True)
    ep.Cache.enable_cache("./endurancepy-cache")
    session = ep.get_session(2019, "WEC", "Spa", "Race")
    session.load(season="08_2018-2019")
    print("Saved", plot(session))


if __name__ == "__main__":
    main()
