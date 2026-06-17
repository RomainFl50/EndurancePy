"""Tour of the lap-level API on a real session (loaded over the network).

Run with::

    python examples/lap_analysis.py

Loads a session via auto-discovery, then showcases the lap API: every
``pick_*`` filter, stint reconstruction, the track-status timeline and the
classification. No CSV path needed.
"""

from __future__ import annotations

from pathlib import Path

import endurancepy as ep
from endurancepy.core import Laps, Session


def _fmt(value: object) -> str:
    return "-" if value is None or str(value) == "NaT" else str(value)


def analyse(session: Session) -> Laps:
    """Print a tour of the lap API for a loaded session; return its laps."""
    laps = session.laps
    classes = sorted(laps["Class"].dropna().unique())
    cars = sorted(laps["CarNumber"].dropna().unique())

    print("=" * 60)
    print(f"{len(laps)} laps | {len(cars)} cars | classes: {', '.join(classes)}")

    fastest = laps.pick_fastest()
    if fastest is not None:
        print(
            f"\nOverall fastest: {_fmt(fastest['LapTime'])} "
            f"(car {fastest['CarNumber']}, {_fmt(fastest['Driver'])})"
        )
    print("Fastest per class:")
    for class_name in classes:
        best = laps.pick_classes(class_name).pick_fastest()
        if best is not None:
            print(
                f"  {class_name:10} {_fmt(best['LapTime'])}  (car {best['CarNumber']})"
            )

    print("\nFilters (pick_*):")
    print(f"  quick laps (<107%): {len(laps.pick_quicklaps())}")
    print(f"  accurate (clean GF): {len(laps.pick_accurate())}")
    print(f"  pit in-laps: {len(laps.pick_box_laps('in'))}")
    print(f"  pit out-laps: {len(laps.pick_box_laps('out'))}")
    print(f"  non-box laps: {len(laps.pick_wo_box())}")
    print(f"  under FCY: {len(laps.pick_track_status('FCY'))}")

    lead_car = cars[0]
    print(f"\nStints for car {lead_car}:")
    for stint, group in laps.pick_cars(lead_car).groupby("Stint"):
        clean = group.pick_wo_box()["LapTime"].dropna()
        best = clean.min() if len(clean) else None
        print(
            f"  stint {int(stint)}: {len(group)} laps"
            + (f", best {_fmt(best)}" if best is not None else "")
        )

    print("\nTrack-status timeline:")
    for _, row in session.track_status.iterrows():
        print(f"  {_fmt(row['Time'])}  {row['Status']}")

    print("\nClassification:")
    shown = session.results[["Position", "CarNumber", "Class", "Crew", "Laps"]].head(10)
    print(shown.to_string(index=False))
    print("=" * 60)
    return laps


def main() -> None:
    Path("./endurancepy-cache").mkdir(exist_ok=True)
    ep.Cache.enable_cache("./endurancepy-cache")
    session = ep.get_session(2019, "WEC", "Spa", "Race")
    session.load(season="08_2018-2019")
    analyse(session)


if __name__ == "__main__":
    main()
