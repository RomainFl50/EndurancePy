"""Compute championship standings from session results (offline).

Run with::

    python examples/standings_example.py path/to/23_Analysis_Race.CSV

For a real championship you'd pass one ``session.results`` per round. Here, to
stay offline and self-contained, we derive results from a single Analysis CSV
and simulate a second round, then aggregate points overall and per class.
"""

from __future__ import annotations

import sys
from pathlib import Path

import endurancepy as ep
from endurancepy.results import from_laps
from endurancepy.standings import Standings


def compute(analysis_csv: str | Path) -> Standings:
    """Build and print example standings; return the overall table."""
    round1 = from_laps(ep.read_analysis(analysis_csv))

    # Simulate a second round with the finishing order reversed (demo only).
    round2 = round1.copy()
    round2["Position"] = round1["Position"].to_numpy()[::-1]

    overall = ep.compute_standings([round1, round2], by="CarNumber")
    print("Overall standings (2 rounds, default points):")
    print(overall.to_string(index=False))

    per_class = ep.compute_standings([round1, round2], by="CarNumber", per_class=True)
    print("\nPer-class standings:")
    print(per_class.to_string(index=False))

    custom = ep.compute_standings(
        [round1, round2], by="CarNumber", points=[10, 6, 4, 2]
    )
    print("\nWith a custom points table [10, 6, 4, 2]:")
    print(custom[["Position", "CarNumber", "Points"]].to_string(index=False))

    return overall


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python examples/standings_example.py <Analysis.CSV>")
    compute(sys.argv[1])
