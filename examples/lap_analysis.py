"""Offline tour of the lap-level API from a local Analysis CSV (no network).

Download an ``..._Analysis_....CSV`` from a results portal, then run::

    python examples/lap_analysis.py path/to/23_Analysis_Race.CSV

Showcases lap parsing, every ``pick_*`` filter, stint reconstruction, the
track-status timeline and the classification derived from the laps.
"""

from __future__ import annotations

import sys
from pathlib import Path

import endurancepy as ep
from endurancepy.core import Laps
from endurancepy.results import from_laps
from endurancepy.track_status import from_laps as track_status_from_laps


def _fmt(value: object) -> str:
    return "-" if value is None or str(value) == "NaT" else str(value)


def analyse(analysis_csv: str | Path) -> Laps:
    """Print a tour of the lap API and return the parsed laps."""
    laps = ep.read_analysis(analysis_csv)
    classes = sorted(laps["Class"].dropna().unique())
    cars = sorted(laps["CarNumber"].dropna().unique())

    print("=" * 60)
    print(f"{len(laps)} laps | {len(cars)} cars | classes: {', '.join(classes)}")

    # --- fastest laps -----------------------------------------------------
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

    # --- pick_* filters ---------------------------------------------------
    print("\nFilters (pick_*):")
    print(f"  quick laps (<107%): {len(laps.pick_quicklaps())}")
    print(f"  accurate (clean GF): {len(laps.pick_accurate())}")
    print(f"  pit in-laps: {len(laps.pick_box_laps('in'))}")
    print(f"  pit out-laps: {len(laps.pick_box_laps('out'))}")
    print(f"  non-box laps: {len(laps.pick_wo_box())}")
    print(f"  under FCY: {len(laps.pick_track_status('FCY'))}")

    # --- stints for the leading car --------------------------------------
    lead_car = cars[0]
    car_laps = laps.pick_cars(lead_car)
    print(f"\nStints for car {lead_car}:")
    for stint, group in car_laps.groupby("Stint"):
        clean = group.pick_wo_box()["LapTime"].dropna()
        best = clean.min() if len(clean) else None
        print(
            f"  stint {int(stint)}: {len(group)} laps"
            + (f", best {_fmt(best)}" if best is not None else "")
        )

    # --- track-status timeline -------------------------------------------
    status = track_status_from_laps(laps)
    print("\nTrack-status timeline:")
    for _, row in status.iterrows():
        print(f"  {_fmt(row['Time'])}  {row['Status']}")

    # --- classification ---------------------------------------------------
    print("\nClassification (from laps):")
    results = from_laps(laps)
    shown = results[["Position", "CarNumber", "Class", "Crew", "Laps"]].head(10)
    print(shown.to_string(index=False))
    print("=" * 60)
    return laps


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python examples/lap_analysis.py <Analysis.CSV>")
    analyse(sys.argv[1])
