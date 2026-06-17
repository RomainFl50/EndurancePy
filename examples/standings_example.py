"""Championship standings from real sessions (loaded over the network).

Run with::

    python examples/standings_example.py

Loads several rounds of a season and aggregates points into a standings table —
overall, per class, and with a custom points system. No CSV path needed.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import pandas as pd

import endurancepy as ep
from endurancepy.standings import Standings


def compute(results: Sequence[pd.DataFrame]) -> Standings:
    """Aggregate and print standings from a list of per-round results."""
    overall = ep.compute_standings(results, by="CarNumber")
    print("Overall standings (default points):")
    print(overall.to_string(index=False))

    per_class = ep.compute_standings(results, by="CarNumber", per_class=True)
    print("\nPer-class standings:")
    print(per_class.to_string(index=False))

    custom = ep.compute_standings(results, by="CarNumber", points=[10, 6, 4, 2])
    print("\nWith a custom points table [10, 6, 4, 2]:")
    print(custom[["Position", "CarNumber", "Points"]].to_string(index=False))
    return overall


def main() -> None:
    Path("./endurancepy-cache").mkdir(exist_ok=True)
    ep.Cache.enable_cache("./endurancepy-cache")

    schedule = ep.get_event_schedule(2019, "WEC", season="08_2018-2019")
    results = []
    for event_name in ("Silverstone", "Fuji", "Shanghai"):
        race = schedule.get_event_by_name(event_name).get_race()
        race.load()
        results.append(race.results)
    compute(results)


if __name__ == "__main__":
    main()
