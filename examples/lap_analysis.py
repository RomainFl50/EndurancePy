"""Analyse a local Al Kamel Analysis CSV (no network needed).

Download an ``..._Analysis_....CSV`` from a results portal, then run::

    python examples/lap_analysis.py path/to/23_Analysis_Race.CSV

This showcases the core, offline API: parsing laps, the ``pick_*`` filters, and
reconstructing the classification from the laps.
"""

from __future__ import annotations

import sys
from pathlib import Path

import endurancepy as ep
from endurancepy.core import Laps
from endurancepy.results import from_laps


def analyse(analysis_csv: str | Path) -> Laps:
    """Print a short analysis of an Analysis CSV and return the parsed laps."""
    laps = ep.read_analysis(analysis_csv)
    cars = sorted(laps["CarNumber"].dropna().unique())
    classes = sorted(laps["Class"].dropna().unique())
    print(f"{len(laps)} laps | {len(cars)} cars | classes: {', '.join(classes)}")

    fastest = laps.pick_fastest()
    if fastest is not None:
        print(
            f"Overall fastest: {fastest['LapTime']} "
            f"(car {fastest['CarNumber']}, {fastest['Driver']})"
        )

    print("\nFastest lap per class:")
    for class_name in classes:
        best = laps.pick_classes(class_name).pick_fastest()
        if best is not None:
            print(f"  {class_name:10} {best['LapTime']}  (car {best['CarNumber']})")

    print("\nClassification (from laps):")
    results = from_laps(laps)
    shown = results[["Position", "CarNumber", "Class", "Crew", "Laps"]].head(10)
    print(shown.to_string(index=False))

    return laps


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python examples/lap_analysis.py <Analysis.CSV>")
    analyse(sys.argv[1])
