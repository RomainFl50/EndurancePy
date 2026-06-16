"""Tests for the configurable championship standings calculator."""

from __future__ import annotations

import pandas as pd

from endurancepy.standings import Standings, compute_standings


def _round(positions: dict[str, int]) -> pd.DataFrame:
    """Build a minimal results frame: car number -> overall position."""
    return pd.DataFrame(
        {
            "CarNumber": list(positions),
            "Position": list(positions.values()),
            "Class": ["LMP1"] * len(positions),
            "PositionInClass": list(positions.values()),
        }
    )


def test_points_accumulate_and_rank() -> None:
    rounds = [_round({"7": 1, "8": 2, "9": 3}), _round({"8": 1, "7": 2, "9": 3})]
    table = compute_standings(rounds, by="CarNumber")
    assert isinstance(table, Standings)
    points = dict(zip(table["CarNumber"], table["Points"], strict=True))
    assert points["7"] == 25 + 18  # P1 + P2
    assert points["8"] == 18 + 25
    assert points["9"] == 15 + 15
    # tie on points (43) broken by wins (1 each) then car number -> 7 ahead of 8
    assert list(table["Position"]) == [1, 2, 3]
    assert table.iloc[0]["CarNumber"] == "7"
    assert dict(zip(table["CarNumber"], table["Wins"], strict=True)) == {
        "7": 1,
        "8": 1,
        "9": 0,
    }


def test_custom_points_sequence() -> None:
    rounds = [_round({"7": 1, "8": 2})]
    table = compute_standings(rounds, by="CarNumber", points=[10, 5])
    points = dict(zip(table["CarNumber"], table["Points"], strict=True))
    assert points == {"7": 10.0, "8": 5.0}


def test_per_class_standings() -> None:
    frame = pd.DataFrame(
        {
            "CarNumber": ["7", "8", "83"],
            "Position": [1, 2, 3],
            "Class": ["HYPERCAR", "HYPERCAR", "LMGT3"],
            "PositionInClass": [1, 2, 1],
        }
    )
    table = compute_standings([frame], by="CarNumber", per_class=True)
    gt3 = table[table["Class"] == "LMGT3"].iloc[0]
    assert gt3["CarNumber"] == "83"
    assert gt3["Position"] == 1  # class winner despite 3rd overall
    assert gt3["Points"] == 25
