"""Quickstart: load a real session straight from the Al Kamel portal.

Requires network access (the portal must be reachable). Run with::

    python examples/quickstart.py

Note: respect the portal's terms of service; the on-disk cache avoids
re-downloading. This example does not ship any Al Kamel data.
"""

from __future__ import annotations

from pathlib import Path

import endurancepy as ep


def main() -> None:
    cache_dir = Path("./endurancepy-cache")
    cache_dir.mkdir(exist_ok=True)
    ep.Cache.enable_cache(cache_dir)

    # 2019 WEC 6 Hours of Spa-Francorchamps (season id "08_2018-2019").
    session = ep.get_session(2019, "WEC", "Spa", "Race")
    session.load(season="08_2018-2019")

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

    print("\nFastest lap per class:")
    for class_name in sorted(laps["Class"].dropna().unique()):
        best = laps.pick_classes(class_name).pick_fastest()
        if best is not None:
            print(f"  {class_name:10} {best['LapTime']}  (car {best['CarNumber']})")


if __name__ == "__main__":
    main()
