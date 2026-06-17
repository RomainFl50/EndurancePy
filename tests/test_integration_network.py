"""End-to-end integration test against the live Al Kamel portal.

Marked ``network`` (skipped in the default CI run) and additionally self-skips
when the portal is unreachable, so it is safe to run anywhere; it is exercised
on demand via the ``integration`` GitHub Actions workflow.
"""

from __future__ import annotations

import urllib.request
from pathlib import Path

import pytest

import endurancepy as ep

_SEASON = "08_2018-2019"
_SEASON_URL = f"https://fiawec.alkamelsystems.com/?season={_SEASON}"


def _portal_reachable() -> bool:
    request = urllib.request.Request(_SEASON_URL, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.status == 200
    except Exception:
        return False


@pytest.mark.network
def test_load_wec_spa_2019_via_discovery(tmp_path: Path) -> None:
    if not _portal_reachable():
        pytest.skip("Al Kamel portal not reachable from this environment")

    ep.Cache.enable_cache(str(tmp_path))
    session = ep.get_session(2019, "WEC", "Spa", "Race")
    session.load(season=_SEASON)

    assert len(session.laps) > 100
    assert len(session.results) > 0
    assert session.results.iloc[0]["Position"] == 1
    assert set(session.laps["Class"].dropna().unique())  # multi-class data present


@pytest.mark.network
def test_event_schedule_via_discovery() -> None:
    if not _portal_reachable():
        pytest.skip("Al Kamel portal not reachable from this environment")

    schedule = ep.get_event_schedule(2019, "WEC", season=_SEASON)
    # a full WEC superseason has many events, not just the last one
    assert len(schedule) > 5
    assert schedule.get_event_by_name("Spa")["EventName"]
    assert schedule.get_event_by_name("Le Mans")["EventName"]


@pytest.mark.network
def test_list_and_resolve_seasons() -> None:
    if not _portal_reachable():
        pytest.skip("Al Kamel portal not reachable from this environment")

    seasons = ep.list_seasons("WEC")
    assert _SEASON in seasons
    # season id resolved automatically from the year (no explicit season=)
    schedule = ep.get_event_schedule(2024, "WEC")
    assert schedule.season == "13_2024"
    assert len(schedule) > 0
