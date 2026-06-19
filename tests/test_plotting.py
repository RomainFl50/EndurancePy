"""Tests for the plotting helpers.

The colour helpers need no backend; the chart tests self-skip without plotly.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from endurancepy import plotting
from endurancepy.alkamel.analysis import read_analysis

HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")
FIXTURE = Path(__file__).parent / "fixtures" / "analysis_sample.csv"


def test_class_color_case_insensitive() -> None:
    assert plotting.get_class_color("HYPERCAR") == plotting.get_class_color("hypercar")
    assert HEX.match(plotting.get_class_color("LMGT3"))


def test_unknown_class_returns_default() -> None:
    assert plotting.get_class_color("does-not-exist") == plotting.DEFAULT_COLOR


def test_manufacturer_color() -> None:
    assert plotting.get_manufacturer_color("Toyota") == "#EB0A1E"
    assert plotting.get_manufacturer_color(
        "ferrari"
    ) == plotting.get_manufacturer_color("FERRARI")
    assert plotting.get_manufacturer_color("nope") == plotting.DEFAULT_COLOR


def test_registries_are_valid_hex() -> None:
    assert plotting.list_classes()
    assert plotting.list_manufacturers()
    for color in (
        *plotting.CLASS_COLORS.values(),
        *plotting.MANUFACTURER_COLORS.values(),
    ):
        assert HEX.match(color)


def test_setup_mpl_if_available() -> None:
    pytest.importorskip("matplotlib")
    plotting.setup_mpl()  # should not raise when matplotlib is installed


def test_plot_strategy_one_bar_per_stint() -> None:
    go = pytest.importorskip("plotly.graph_objects")
    laps = read_analysis(FIXTURE)
    fig = plotting.plot_strategy(laps)

    assert isinstance(fig, go.Figure)
    # one trace per class, coloured by the class palette
    assert [t.name for t in fig.data] == ["HYPERCAR", "LMGT3"]
    assert fig.data[0].marker.color == plotting.get_class_color("HYPERCAR")
    # one bar per (car, stint): car 7 pits & changes driver -> 2 stints
    assert sum(len(t.y) for t in fig.data) == 4
    hypercar = fig.data[0]
    car7 = [
        (base, length)
        for car, base, length in zip(hypercar.y, hypercar.base, hypercar.x, strict=True)
        if car == "7"
    ]
    assert car7 == [(1, 2), (3, 2)]  # laps 1-2 then 3-4
    # cars ordered by class then number
    assert fig.layout.yaxis.categoryarray == ("7", "8", "83")


def test_plot_strategy_empty_laps() -> None:
    pytest.importorskip("plotly.graph_objects")
    laps = read_analysis(FIXTURE).iloc[0:0]
    fig = plotting.plot_strategy(laps)
    assert len(fig.data) == 0  # no bars, but a valid (empty) figure


def test_get_car_style_is_deterministic_and_class_coloured() -> None:
    a = plotting.get_car_style("7", "HYPERCAR")
    assert a == plotting.get_car_style("7", "HYPERCAR")  # stable
    assert a["color"] == plotting.get_class_color("HYPERCAR")
    # cars sharing a class colour get a different dash/marker
    b = plotting.get_car_style("8", "HYPERCAR")
    assert a["color"] == b["color"]
    assert (a["dash"], a["symbol"]) != (b["dash"], b["symbol"])


@pytest.mark.parametrize(
    "name",
    [
        "plot_lap_evolution",
        "plot_position_evolution",
        "plot_gap",
        "plot_race_trace",
    ],
)
def test_line_charts_one_trace_per_car(name: str) -> None:
    go = pytest.importorskip("plotly.graph_objects")
    laps = read_analysis(FIXTURE)
    fig = getattr(plotting, name)(laps)
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 3  # cars 7, 8, 83


def test_plot_pace_one_box_per_class() -> None:
    pytest.importorskip("plotly.graph_objects")
    fig = plotting.plot_pace(read_analysis(FIXTURE))
    assert [t.name for t in fig.data] == ["HYPERCAR", "LMGT3"]


def test_add_track_status_shades_field_neutralisations() -> None:
    pytest.importorskip("plotly.graph_objects")
    laps = read_analysis(FIXTURE)
    # No field-wide neutralisation in the fixture -> no bands.
    plain = plotting.add_track_status(plotting.plot_gap(laps), laps)
    assert len(plain.layout.shapes) == 0
    # Make lap 2 a full-field FCY -> one shaded band.
    laps.loc[laps["LapNumber"] == 2, "TrackStatus"] = "FCY"
    shaded = plotting.add_track_status(plotting.plot_gap(laps), laps)
    assert len(shaded.layout.shapes) == 1
