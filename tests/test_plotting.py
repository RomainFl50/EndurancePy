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


def test_setup_mpl_dark_theme() -> None:
    plt = pytest.importorskip("matplotlib.pyplot")
    plotting.setup_mpl(theme="dark")
    assert plt.rcParams["figure.facecolor"] == "#111418"
    plotting.setup_mpl(theme="light")  # restore


def test_laptime_axis_formatter() -> None:
    pytest.importorskip("matplotlib")
    fmt = plotting.laptime_formatter()
    assert fmt(118.056, None) == "1:58.056"  # 118.056s -> M:SS.mmm


def test_format_time_axis_sets_formatter() -> None:
    plt = pytest.importorskip("matplotlib.pyplot")
    _, ax = plt.subplots()
    assert plotting.format_time_axis(ax, "y") is ax
    assert ax.yaxis.get_major_formatter()(94.5, None) == "1:34.500"
    plt.close("all")


def test_get_team_color() -> None:
    # matched on a distinctive substring, case-insensitive
    assert (
        plotting.get_team_color("Ferrari AF Corse #51")
        == plotting.TEAM_COLORS["AF CORSE"]
    )
    assert plotting.get_team_color("iron dames") == plotting.TEAM_COLORS["IRON DAMES"]
    assert plotting.get_team_color("Unknown Team") == plotting.DEFAULT_COLOR
    assert plotting.list_teams()


def test_plot_strategy_one_bar_per_stint() -> None:
    go = pytest.importorskip("plotly.graph_objects")
    laps = read_analysis(FIXTURE)
    fig = plotting.plot_strategy(laps)

    assert isinstance(fig, go.Figure)
    bars = [t for t in fig.data if t.type == "bar"]
    # one bar trace per class, coloured by the class palette
    assert [t.name for t in bars] == ["HYPERCAR", "LMGT3"]
    assert bars[0].marker.color == plotting.get_class_color("HYPERCAR")
    # one bar per (car, stint): car 7 pits & changes driver -> 2 stints
    assert sum(len(t.y) for t in bars) == 4
    car7 = [
        (base, length)
        for car, base, length in zip(bars[0].y, bars[0].base, bars[0].x, strict=True)
        if car == "7"
    ]
    assert car7 == [(1, 2), (3, 2)]  # laps 1-2 then 3-4
    assert fig.layout.yaxis.categoryarray == ("7", "8", "83")


def test_plot_strategy_marks_driver_changes() -> None:
    pytest.importorskip("plotly.graph_objects")
    laps = read_analysis(FIXTURE)
    fig = plotting.plot_strategy(laps)
    changes = [t for t in fig.data if t.name == "Driver change"]
    assert len(changes) == 1
    assert list(changes[0].x) == [3]  # car 7's 2nd stint (driver A -> B) starts lap 3
    # opt-out removes the markers
    plain = plotting.plot_strategy(laps, show_driver_changes=False)
    assert not [t for t in plain.data if t.name == "Driver change"]


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


def test_plot_pace_violin() -> None:
    pytest.importorskip("plotly.graph_objects")
    fig = plotting.plot_pace(read_analysis(FIXTURE), kind="violin")
    assert [t.type for t in fig.data] == ["violin", "violin"]


def test_plot_fastest_laps_delta_to_best() -> None:
    pytest.importorskip("plotly.graph_objects")
    fig = plotting.plot_fastest_laps(read_analysis(FIXTURE))
    assert [t.name for t in fig.data] == ["HYPERCAR", "LMGT3"]
    # cars ordered quickest-first; the overall best gets a zero-length bar
    assert fig.layout.yaxis.categoryarray == ("7", "8", "83")
    assert fig.data[0].x[0] == 0.0  # car 7, fastest overall
    assert fig.data[0].x[1] == 0.5  # car 8, +0.5s


def test_plot_stint_pace_one_line_per_stint() -> None:
    pytest.importorskip("plotly.graph_objects")
    laps = read_analysis(FIXTURE)
    assert len(plotting.plot_stint_pace(laps).data) == 4  # car 7 has 2 stints
    assert [t.name for t in plotting.plot_stint_pace(laps, car="7").data] == [
        "#7 stint 1",
        "#7 stint 2",
    ]


def test_plot_driver_comparison_one_box_per_driver() -> None:
    pytest.importorskip("plotly.graph_objects")
    fig = plotting.plot_driver_comparison(read_analysis(FIXTURE), "7")
    assert [t.name for t in fig.data] == ["A AAA", "B BBB"]


def test_plot_top_speeds_one_box_per_class() -> None:
    pytest.importorskip("plotly.graph_objects")
    fig = plotting.plot_top_speeds(read_analysis(FIXTURE))
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
