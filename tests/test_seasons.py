"""Offline tests for season listing and year -> season resolution."""

from __future__ import annotations

from typing import Any

import pytest

import endurancepy as ep
from endurancepy.exceptions import SessionNotAvailableError


@pytest.fixture(autouse=True)
def _patch_json(mock_manifests: Any) -> None:
    paths = [
        (
            f"wec/results/{s}/04_LE MANS/267_FIA WEC/"
            "202406151600_Race/24_Hour 24/23_Analysis_Race_Hour 24.CSV"
        )
        for s in ("08_2018-2019", "13_2024", "14_2025")
    ]
    mock_manifests(paths, ("08_2018-2019", "13_2024", "14_2025"))


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
