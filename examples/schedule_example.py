"""Browse seasons and a season calendar, then load an event (needs network).

Run with::

    python examples/schedule_example.py

Lists the available seasons for a series, builds a year's calendar (the season
id is resolved automatically from the year), then loads one race.
"""

from __future__ import annotations

from pathlib import Path

import endurancepy as ep


def main(series: str = "WEC", year: int = 2019) -> None:
    ep.set_log_level("INFO")  # show discovery/download progress on stderr
    Path("./endurancepy-cache").mkdir(exist_ok=True)
    ep.Cache.enable_cache("./endurancepy-cache")

    print(f"Available {series} seasons: {ep.list_seasons(series)}")

    schedule = ep.get_event_schedule(year, series)  # season id resolved from year
    print(f"\n{series} {year} ({schedule.season}) — {len(schedule)} events:")
    print(schedule[["RoundNumber", "EventName"]].to_string(index=False))

    event = schedule.get_event_by_name("Le Mans")
    # date and sessions live on the event's own page (fetched on demand)
    print(f"\n{event['EventName']} on {event.get_date():%Y-%m-%d}")
    print(f"Sessions: {', '.join(event.get_sessions())}")

    session = event.get_race()  # already knows its season
    session.load()
    winner = session.results.iloc[0]["CarNumber"]
    print(f"Race: {len(session.laps)} laps, winner car {winner}")


if __name__ == "__main__":
    main()
