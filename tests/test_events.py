"""Offline tests for event/schedule building (no network)."""

from __future__ import annotations

import datetime as dt

import pandas as pd

from endurancepy.alkamel.discovery import build_events, index_page, session_datetime
from endurancepy.core import Session
from endurancepy.events import EventSchedule, Series

_SPA = "Results/08_2018-2019/07_SPA FRANCORCHAMPS/267_FIA WEC"
_LM = "Results/08_2018-2019/08_LE MANS/276_FIA WEC"
_PORSCHE = "Results/08_2018-2019/07_SPA FRANCORCHAMPS/268_Porsche Carrera Cup"
_PATHS = [
    f"{_SPA}/201905021200_Free Practice 1/23_Analysis_Free Practice 1.CSV",
    f"{_SPA}/201905041330_Race/Hour 6/23_Analysis_Race_Hour 6.CSV",
    f"{_LM}/201906151500_Race/24_Hour 24/23_Analysis_Race_Hour 24.CSV",
    f"{_PORSCHE}/201905031630_Race 1/23_Analysis_Race 1.CSV",
]
_HTML = "".join(f'<a href="{p}">x</a>' for p in _PATHS)
_RECORDS = index_page(_HTML)


def test_session_datetime() -> None:
    assert session_datetime("201905041330_Race") == dt.datetime(2019, 5, 4, 13, 30)
    assert session_datetime("no-timestamp_Race") is None


def test_build_events_filters_and_orders() -> None:
    events = build_events(_RECORDS, series_keyword="WEC")
    assert [e.round for e in events] == [7, 8]  # ordered by round, Porsche excluded
    spa = events[0]
    assert spa.name == "SPA FRANCORCHAMPS"
    assert set(spa.sessions) == {"Free Practice 1", "Race"}
    assert spa.date == dt.datetime(2019, 5, 4, 13, 30)  # latest session = race


def _schedule() -> EventSchedule:
    frame = pd.DataFrame(
        {
            "RoundNumber": [7, 8],
            "EventName": ["SPA FRANCORCHAMPS", "LE MANS"],
            "EventDate": [dt.datetime(2019, 5, 4), dt.datetime(2019, 6, 15)],
            "Sessions": [["Free Practice 1", "Race"], ["Race"]],
            "Series": ["WEC", "WEC"],
            "Season": ["08_2018-2019", "08_2018-2019"],
        }
    )
    return EventSchedule(frame, year=2019, series=Series.WEC, season="08_2018-2019")


def test_get_event_by_name_and_round() -> None:
    schedule = _schedule()
    assert schedule.get_event_by_name("Spa")["EventName"] == "SPA FRANCORCHAMPS"
    assert schedule.get_event_by_round(8)["EventName"] == "LE MANS"


def test_event_get_session_carries_season() -> None:
    event = _schedule().get_event_by_name("Le Mans")
    session = event.get_session("Race")
    assert isinstance(session, Session)
    assert session.name == "Race"
    assert session.event == "LE MANS"
    assert session.series is Series.WEC
    assert session.default_season == "08_2018-2019"
