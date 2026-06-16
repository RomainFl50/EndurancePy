"""Browse a season calendar and load one event (needs network).

Run with::

    python examples/schedule_example.py

Lists a season's events for a series, then loads one race via the schedule.
Season ids look like ``"08_2018-2019"`` / ``"13_2024"`` (see the portal URL).
"""

from __future__ import annotations

from pathlib import Path

import endurancepy as ep


def main(series: str = "WEC", season: str = "08_2018-2019", year: int = 2019) -> None:
    cache_dir = Path("./endurancepy-cache")
    cache_dir.mkdir(exist_ok=True)
    ep.Cache.enable_cache(cache_dir)

    schedule = ep.get_event_schedule(year, series, season=season)
    print(f"{series} {season} - {len(schedule)} events:")
    print(schedule[["RoundNumber", "EventName", "EventDate"]].to_string(index=False))

    event = schedule.get_event_by_name("Le Mans")
    print(f"\n{event['EventName']} sessions: {', '.join(event['Sessions'])}")

    session = event.get_race()  # already knows its season
    session.load()
    winner = session.results.iloc[0]["CarNumber"]
    print(f"Race: {len(session.laps)} laps, winner car {winner}")


if __name__ == "__main__":
    main()
