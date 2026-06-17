"""Offline tests for season listing and year -> season resolution."""

from __future__ import annotations

import pytest

import endurancepy as ep
from endurancepy.exceptions import SessionNotAvailableError

# A landing page whose <select name="season"> lists a few WEC seasons.
_LANDING = """
<select name="season">
  <option value="">Select a season</option>
  <option value="08_2018-2019">2018 - 2019</option>
  <option value="13_2024">2024</option>
  <option value="14_2025">2025</option>
</select>
"""


def _fake_download(url: str) -> bytes:
    if "?season=" in url:
        season = url.split("season=")[1].split("&")[0]
        path = (
            f"Results/{season}/04_LE MANS/267_FIA WEC/"
            "202406151600_Race/Hour 24/23_Analysis_Race_Hour 24.CSV"
        )
        return f'<a href="{path}">x</a>'.encode()
    return _LANDING.encode()


@pytest.fixture(autouse=True)
def _patch_download(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("endurancepy.alkamel.client.download", _fake_download)


def test_list_seasons() -> None:
    assert ep.list_seasons("WEC") == ["08_2018-2019", "13_2024", "14_2025"]


def test_schedule_resolves_season_from_year() -> None:
    schedule = ep.get_event_schedule(2024, "WEC")  # no season id given
    assert schedule.season == "13_2024"
    assert len(schedule) >= 1


def test_schedule_resolves_superseason_start_year() -> None:
    assert ep.get_event_schedule(2018, "WEC").season == "08_2018-2019"


def test_unknown_year_raises() -> None:
    with pytest.raises(SessionNotAvailableError):
        ep.get_event_schedule(2099, "WEC")
