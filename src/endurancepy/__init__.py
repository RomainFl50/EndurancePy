"""EndurancePy — endurance racing timing & results data in Python.

Inspired by `FastF1 <https://github.com/theOehrly/Fast-F1>`_, EndurancePy
provides convenient, pandas-based access to timing and results data for endurance
racing series (WEC, ELMS, Asian Le Mans Series, Le Mans Cup, IMSA), built on top
of the publicly available Al Kamel Systems archives.

Quick start::

    import endurancepy as ep

    ep.Cache.enable_cache("./cache")
    session = ep.get_session(2019, "WEC", "Spa", "Race")
    session.load(season="08_2018-2019")   # discover + download automatically
    session.laps, session.results, session.weather_data

Or parse a local Analysis CSV directly with :func:`read_analysis`.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from endurancepy.alkamel.analysis import read_analysis
from endurancepy.alkamel.classification import read_classification
from endurancepy.alkamel.weather import read_weather
from endurancepy.cache import Cache
from endurancepy.events import (
    Event,
    EventSchedule,
    Series,
    get_event,
    get_event_schedule,
    get_session,
)
from endurancepy.logger import set_log_level

try:
    __version__ = version("endurancepy")
except PackageNotFoundError:  # pragma: no cover - not installed (e.g. source tree)
    __version__ = "0.0.0"

__all__ = [
    "Cache",
    "Event",
    "EventSchedule",
    "Series",
    "__version__",
    "get_event",
    "get_event_schedule",
    "get_session",
    "read_analysis",
    "read_classification",
    "read_weather",
    "set_log_level",
]
