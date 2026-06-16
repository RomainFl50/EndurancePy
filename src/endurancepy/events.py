"""Series registry and the event/schedule layer.

Defines the supported :class:`Series` (each mapped to its Al Kamel results host)
and the top-level entry points :func:`get_session`, :func:`get_event` and
:func:`get_event_schedule`. Event discovery and schedule building land in a
later milestone (2.5) and currently raise :class:`NotImplementedError`.
"""

from __future__ import annotations

from enum import Enum

import pandas as pd

from endurancepy.core import Session
from endurancepy.exceptions import SeriesNotSupportedError

__all__ = [
    "Event",
    "EventSchedule",
    "Series",
    "get_event",
    "get_event_schedule",
    "get_session",
]


class Series(Enum):
    """Supported endurance championships, mapped to their Al Kamel results host."""

    WEC = "fiawec.alkamelsystems.com"
    ELMS = "elms.alkamelsystems.com"
    ASLMS = "alms.alkamelsystems.com"
    LMC = "lemanscup.alkamelsystems.com"
    IMSA = "imsa.results.alkamelcloud.com"

    @property
    def host(self) -> str:
        """The base host of the series' Al Kamel results portal."""
        return self.value

    @property
    def keyword(self) -> str:
        """A substring identifying this series' folder on the portal."""
        return _SERIES_KEYWORDS[self]

    @classmethod
    def coerce(cls, series: str | Series) -> Series:
        """Coerce a string (e.g. ``"WEC"``) or :class:`Series` into a Series.

        Raises
        ------
        SeriesNotSupportedError
            If the value does not match a known series.
        """
        if isinstance(series, cls):
            return series
        try:
            return cls[str(series).strip().upper()]
        except KeyError as exc:
            supported = ", ".join(s.name for s in cls)
            raise SeriesNotSupportedError(
                f"Unknown series {series!r}. Supported: {supported}."
            ) from exc


#: Substring identifying each series' folder name on the Al Kamel portal.
_SERIES_KEYWORDS: dict[Series, str] = {
    Series.WEC: "WEC",
    Series.ELMS: "European Le Mans",
    Series.ASLMS: "Asian Le Mans",
    Series.LMC: "Le Mans Cup",
    Series.IMSA: "IMSA",
}


class EventSchedule(pd.DataFrame):
    """A season's calendar for a given series (one row per event)."""

    _metadata = ["year", "series"]

    @property
    def _constructor(self) -> type[EventSchedule]:
        return EventSchedule

    @property
    def _constructor_sliced(self) -> type[Event]:
        return Event


class Event(pd.Series):
    """A single event (race weekend / meeting)."""

    _metadata = ["year", "series"]

    @property
    def _constructor(self) -> type[Event]:
        return Event

    @property
    def _constructor_expanddim(self) -> type[EventSchedule]:
        return EventSchedule


def get_session(
    year: int,
    series: str | Series,
    event: str | int,
    session: str | int,
) -> Session:
    """Create a :class:`~endurancepy.core.Session` (without loading its data).

    Parameters
    ----------
    year:
        Season year, e.g. ``2024``.
    series:
        The championship, e.g. ``"WEC"`` or :attr:`Series.WEC`.
    event:
        Event name (fuzzy-matched) or round number.
    session:
        Session name/abbreviation (e.g. ``"Race"``, ``"FP1"``, ``"Q"``).

    Returns
    -------
    Session
        An unloaded session object. Call :meth:`Session.load` to fetch data.
    """
    resolved = Series.coerce(series)
    return Session(year=year, series=resolved, event=event, name=str(session))


def get_event(year: int, series: str | Series, event: str | int) -> Event:
    """Create an :class:`Event` for a given season, series and event.

    Not implemented yet (milestone 2.5).
    """
    Series.coerce(series)
    raise NotImplementedError


def get_event_schedule(year: int, series: str | Series) -> EventSchedule:
    """Create the :class:`EventSchedule` for a season of a given series.

    Not implemented yet (milestone 2.5).
    """
    Series.coerce(series)
    raise NotImplementedError
