"""Tests for resolving a session's files from discovered records (offline)."""

from __future__ import annotations

from endurancepy.alkamel.discovery import index_page, resolve_session_files

_SPA = "Results/08_2018-2019/07_SPA FRANCORCHAMPS/267_FIA WEC"
_PORSCHE = "Results/08_2018-2019/07_SPA FRANCORCHAMPS/268_Porsche Carrera Cup"

_PATHS = [
    f"{_SPA}/201905021200_Free Practice 1/23_Analysis_Free Practice 1.CSV",
    f"{_SPA}/201905021200_Free Practice 1/03_Classification_Free Practice 1.CSV",
    f"{_SPA}/201905021200_Free Practice 1/26_Weather_Free Practice 1.CSV",
    f"{_SPA}/201905041330_Race/Hour 1/23_Analysis_Race_Hour 1.CSV",
    f"{_SPA}/201905041330_Race/Hour 1/05_Classification_Race_Hour 1.CSV",
    f"{_SPA}/201905041330_Race/Hour 1/26_Weather_Race_Hour 1.CSV",
    f"{_SPA}/201905041330_Race/Hour 2/23_Analysis_Race_Hour 2.CSV",
    f"{_SPA}/201905041330_Race/Hour 2/05_Classification_Race_Hour 2.CSV",
    f"{_SPA}/201905041330_Race/Hour 2/26_Weather_Race_Hour 2.CSV",
    f"{_PORSCHE}/201905031630_Race 1/23_Analysis_Race 1.CSV",
]
_HTML = "".join(f'<a href="{p}">x</a>' for p in _PATHS)
_RECORDS = index_page(_HTML)


def test_resolves_race_to_latest_hour() -> None:
    files = resolve_session_files(
        _RECORDS, event="Spa", session="Race", series_keyword="WEC"
    )
    assert files["analysis"].hour == 2
    assert files["analysis"].filename == "23_Analysis_Race_Hour 2.CSV"
    assert files["classification"].hour == 2
    assert files["weather"].hour == 2


def test_resolves_practice_session() -> None:
    files = resolve_session_files(
        _RECORDS, event="Spa", session="Free Practice 1", series_keyword="WEC"
    )
    assert files["analysis"].hour is None
    assert "Free Practice 1" in files["analysis"].session


def test_series_keyword_filters_out_other_series() -> None:
    files = resolve_session_files(
        _RECORDS, event="Spa", session="Race", series_keyword="WEC"
    )
    # the Porsche Carrera Cup race must not be selected
    assert files["analysis"].series == "267_FIA WEC"
