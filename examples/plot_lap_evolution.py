"""Plot lap-time evolution for a real session (loaded over the network).

Requires the plotting extra (``pip install endurancepy[plot]``). Run with::

    python examples/plot_lap_evolution.py

Each clean (green-flag, non-pit) lap is plotted as lap time vs lap number, one
colour per class — a quick look at pace, traffic and degradation. No CSV needed.
"""

from __future__ import annotations

from pathlib import Path

import endurancepy as ep
from endurancepy import plotting
from endurancepy.core import Session


def plot(session: Session, output: str | Path = "lap_evolution.png") -> Path:
    """Render the lap-time evolution scatter for a loaded session."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    laps = session.laps
    clean = laps.pick_wo_box()
    green = clean.pick_track_status("GF")
    # Older seasons (e.g. 2018-2019) have no per-lap flag column, so green-flag
    # filtering would drop every lap; fall back to all non-pit laps in that case.
    clean = green if len(green) else clean

    fig, ax = plt.subplots(figsize=(9, 5))
    seen: set[str] = set()
    for class_name in sorted(laps["Class"].dropna().unique()):
        color = plotting.get_class_color(class_name)
        for _, car_laps in clean.pick_classes(class_name).groupby("CarNumber"):
            ax.plot(
                car_laps["LapNumber"],
                car_laps["LapTime"].dt.total_seconds(),
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


def main() -> None:
    ep.set_log_level("INFO")  # show discovery/download progress on stderr
    Path("./endurancepy-cache").mkdir(exist_ok=True)
    ep.Cache.enable_cache("./endurancepy-cache")
    session = ep.get_session(2019, "WEC", "Spa", "Race")
    session.load(season="08_2018-2019")
    print("Saved", plot(session))


if __name__ == "__main__":
    main()
