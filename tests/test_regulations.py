"""Tests for the stored championship regulations (offline)."""

from __future__ import annotations

import pandas as pd
import pytest

import endurancepy as ep
from endurancepy.exceptions import (
    RegulationsNotAvailableError,
    SeriesNotSupportedError,
)


def test_list_regulations() -> None:
    available = ep.list_regulations()
    assert ("WEC", 2024) in available
    assert ("IMSA", 2024) in available
    # filtering by series
    assert all(series == "WEC" for series, _ in ep.list_regulations("WEC"))


def test_wec_2024_points() -> None:
    reg = ep.regulations("WEC", 2024)
    assert reg.series == "WEC"
    assert reg.season == 2024
    assert reg.points.race == (25, 18, 15, 12, 10, 8, 6, 4, 2, 1)
    assert reg.points.pole == 1
    assert reg.points.le_mans_multiplier == 1.5
    assert reg.points.per_class is True
    assert reg.status == "verified"
    assert "Hypercar" in reg.classes


def test_imsa_2024_points() -> None:
    reg = ep.regulations("IMSA", 2024)
    assert reg.points.race[0] == 350  # class win
    assert reg.status == "approximate"


def test_every_file_keeps_a_source_url() -> None:
    # the whole point of the store: each file records where it came from
    for series, year in ep.list_regulations():
        reg = ep.regulations(series, year)
        assert reg.sources, f"{series} {year} has no source"
        assert all(s.url.startswith("http") for s in reg.sources)


def test_unknown_season_raises() -> None:
    with pytest.raises(RegulationsNotAvailableError):
        ep.regulations("WEC", 1999)


def test_unknown_series_raises() -> None:
    with pytest.raises(SeriesNotSupportedError):
        ep.regulations("NASCAR", 2024)


def test_standings_use_regulations_points() -> None:
    reg = ep.regulations("WEC", 2024)
    result = pd.DataFrame(
        {
            "CarNumber": ["7", "8"],
            "Position": [1, 2],
            "PositionInClass": [1, 2],
            "Class": ["Hypercar", "Hypercar"],
        }
    )
    table = ep.compute_standings([result, result], regulations=reg)
    points = dict(zip(table["CarNumber"], table["Points"], strict=True))
    assert points["7"] == 50.0  # 25 x 2 rounds
    assert points["8"] == 36.0  # 18 x 2
    # per_class flag came from the regulations (Class column present)
    assert "Class" in table.columns
