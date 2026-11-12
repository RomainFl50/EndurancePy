"""Offline tests for season driver pace (endurancepy.pace.driver_pace)."""

from __future__ import annotations

import pandas as pd

from endurancepy.pace import driver_pace


def _laps(car, driver, cls, base_s, n=20, start=2):
    """A synthetic clean stint: n timed laps, base + 0.1s drift, no pit/opening."""
    rows = []
    for i in range(n):
        rows.append(
            {
                "CarNumber": car,
                "Driver": driver,
                "Class": cls,
                "LapNumber": start + i,
                "LapTime": pd.to_timedelta(base_s + i * 0.1, unit="s"),
                "PitInTime": pd.NaT,
                "PitOutTime": pd.NaT,
                "IsAccurate": True,
            }
        )
    return rows


def _frame(*stints):
    rows = []
    for s in stints:
        rows.extend(s)
    return pd.DataFrame(rows)


def test_gap_is_relative_to_class_best_and_aggregates_across_races() -> None:
    race1 = _frame(
        _laps("92", "Richard Lietz", "LMGT3", 100.0),
        _laps("92", "Yasser Shahin", "LMGT3", 101.0),
        _laps("33", "Ben Keating", "LMGT3", 102.0),
        _laps("8", "Brendon Hartley", "HYPERCAR", 90.0),  # own class reference
    )
    race2 = _frame(
        _laps("92", "Richard Lietz", "LMGT3", 100.0),
        _laps("92", "Yasser Shahin", "LMGT3", 100.5),
    )
    cats = {"Richard LIETZ": "P", "Yasser Shahin": "B", "Ben Keating": "B"}
    table = driver_pace([race1, race2], categories=cats)
    by = {r.Driver: r for r in table.itertuples()}

    # Lietz is the class reference in both races -> 0 % mean gap.
    assert abs(by["Richard Lietz"].MeanGapPercent) < 1e-9
    assert by["Richard Lietz"].Category == "P"
    assert by["Richard Lietz"].Races == 2
    # Shahin: race1 top-5 mean 101.2 vs 100.2 (+0.998%), race2 100.7 vs 100.2 (+0.499%).
    expected = (100 * (101.2 / 100.2 - 1) + 100 * (100.7 / 100.2 - 1)) / 2
    assert abs(by["Yasser Shahin"].MeanGapPercent - expected) < 1e-9
    assert by["Yasser Shahin"].Category == "B"
    # Hartley is alone in HYPERCAR -> its own reference, 0 %.
    assert abs(by["Brendon Hartley"].MeanGapPercent) < 1e-9
    assert by["Brendon Hartley"].Category == ""  # not supplied
    # Sorted by mean gap ascending.
    assert list(table["MeanGapPercent"]) == sorted(table["MeanGapPercent"])


def test_excludes_pit_opening_and_inaccurate_laps_and_min_laps() -> None:
    stint = _laps("7", "Mike Conway", "HYPERCAR", 95.0, n=12)
    # Pollute with laps that must be ignored.
    extra = [
        {
            "CarNumber": "7",
            "Driver": "Mike Conway",
            "Class": "HYPERCAR",
            "LapNumber": 1,
            "LapTime": pd.to_timedelta(60.0, unit="s"),
            "PitInTime": pd.NaT,
            "PitOutTime": pd.NaT,
            "IsAccurate": True,
        },
        {
            "CarNumber": "7",
            "Driver": "Mike Conway",
            "Class": "HYPERCAR",
            "LapNumber": 50,
            "LapTime": pd.to_timedelta(60.0, unit="s"),
            "PitInTime": pd.Timestamp("2026-01-01"),
            "PitOutTime": pd.NaT,
            "IsAccurate": True,
        },
        {
            "CarNumber": "7",
            "Driver": "Mike Conway",
            "Class": "HYPERCAR",
            "LapNumber": 51,
            "LapTime": pd.to_timedelta(60.0, unit="s"),
            "PitInTime": pd.NaT,
            "PitOutTime": pd.NaT,
            "IsAccurate": False,
        },
    ]
    table = driver_pace([pd.DataFrame(stint + extra)])
    row = table[table["Driver"] == "Mike Conway"].iloc[0]
    assert row["Laps"] == 12  # only the clean stint counts

    # Below min_laps -> dropped entirely.
    short = driver_pace(
        [pd.DataFrame(_laps("7", "Mike Conway", "HYPERCAR", 95.0, n=9))]
    )
    assert short.empty


def test_category_match_tolerates_word_order_and_accents() -> None:
    race = _frame(
        _laps("12", "Will Stevens", "HYPERCAR", 94.0),
        _laps("8", "Sébastien Bourdais", "HYPERCAR", 94.5),
    )
    cats = {"STEVENS WILL": "P", "Sebastien BOURDAIS": "P"}
    table = driver_pace([race], categories=cats)
    cat = {r.Driver: r.Category for r in table.itertuples()}
    assert cat["Will Stevens"] == "P"  # reversed word order
    assert cat["Sébastien Bourdais"] == "P"  # accent difference


def test_empty_input_returns_typed_empty_frame() -> None:
    table = driver_pace([])
    assert table.empty
    assert list(table.columns) == [
        "Driver",
        "Category",
        "Class",
        "MeanGapPercent",
        "Races",
        "Laps",
    ]
