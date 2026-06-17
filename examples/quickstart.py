"""Quickstart: load a real session from the Al Kamel portal and summarise it.

Requires network access. Run with::

    python examples/quickstart.py

No CSV needed — the session is discovered and downloaded automatically. The
on-disk cache avoids re-downloading; no Al Kamel data ships with the project.
"""

from __future__ import annotations

from pathlib import Path

import endurancepy as ep
from endurancepy.core import Session


def summarise(session: Session) -> None:
    """Print a short summary of a loaded session."""
    laps = session.laps
    print(f"Loaded {len(laps)} laps for {len(session.cars)} cars\n")

    print("Top 5 overall:")
    top = session.results.head(5)
    print(
        top[["Position", "CarNumber", "Class", "Crew", "Laps"]].to_string(index=False)
    )

    fastest = laps.pick_fastest()
    if fastest is not None:
        print(
            f"\nFastest lap: {fastest['LapTime']} "
            f"by car {fastest['CarNumber']} ({fastest['Driver']})"
        )


def main() -> None:
    Path("./endurancepy-cache").mkdir(exist_ok=True)
    ep.Cache.enable_cache("./endurancepy-cache")

    # 2019 WEC 6 Hours of Spa-Francorchamps (season id "08_2018-2019").
    session = ep.get_session(2019, "WEC", "Spa", "Race")
    session.load(season="08_2018-2019")
    summarise(session)


if __name__ == "__main__":
    main()
