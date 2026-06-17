"""Series registry and the event/schedule layer.

Defines the supported :class:`Series` (each mapped to its Al Kamel results host)
and the top-level entry points :func:`get_session`, :func:`get_event` and
:func:`get_event_schedule`.

Season calendars are built by discovering a portal ``?season=`` page (the season
id, e.g. ``"08_2018-2019"``, is supplied by the caller — the portal's season
selector is a JS menu that is not scrapeable from static HTML).
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Any

import pandas as pd
from rapidfuzz import fuzz

from endurancepy.core import Session
from endurancepy.exceptions import SeriesNotSupportedError, SessionNotAvailableError

__all__ = [
    "Event",
    "EventSchedule",
    "Series",
    "get_event",
    "get_event_schedule",
    "get_session",
    "list_seasons",
]

#: Parse a season id (``NN_YYYY`` or ``NN_YYYY-YYYY``) into its starting year.
_SEASON_YEAR_RE = re.compile(r"^\d+_(\d{4})(?:-\d{4})?$")


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

#: Column dtypes of an :class:`EventSchedule`.
_SCHEDULE_DTYPES: dict[str, str] = {
    "RoundNumber": "Int64",
    "EventName": "string",
    "EventFolder": "string",
    "EventDate": "datetime64[ns]",
    "Sessions": "object",
    "Series": "string",
    "Season": "string",
}


def _match_name(query: str, candidates: list[str]) -> str:
    """Best name match: substring containment (shortest), else partial_ratio."""
    if not candidates:
        raise SessionNotAvailableError(f"No events to match {query!r} against.")
    needle = str(query).strip().lower()
    contains = [c for c in candidates if needle in c.lower()]
    if contains:
        return min(contains, key=len)
    return max(candidates, key=lambda c: fuzz.partial_ratio(needle, c.lower()))


class EventSchedule(pd.DataFrame):
    """A season's calendar for a given series (one row per event)."""

    _metadata = ["year", "series", "season"]

    def __init__(
        self,
        *args: Any,
        year: int = 0,
        series: Series | None = None,
        season: str | None = None,
        **kwargs: Any,
    ):
        super().__init__(*args, **kwargs)
        self.year = year
        self.series = series
        self.season = season

    @property
    def _constructor(self) -> type[EventSchedule]:
        return EventSchedule

    @property
    def _constructor_sliced(self) -> type[Event]:
        return Event

    def get_event_by_round(self, round_number: int) -> Event:
        """Return the :class:`Event` with the given round number."""
        match = self[self["RoundNumber"] == round_number]
        if len(match) == 0:
            raise SessionNotAvailableError(f"No event with round {round_number}.")
        return match.iloc[0]

    def get_event_by_name(self, name: str) -> Event:
        """Return the :class:`Event` whose name best matches ``name``."""
        chosen = _match_name(name, [str(n) for n in self["EventName"]])
        return self[self["EventName"] == chosen].iloc[0]


class Event(pd.Series):
    """A single event (race weekend / meeting)."""

    _metadata = ["year", "series", "season"]

    @property
    def _constructor(self) -> type[Event]:
        return Event

    @property
    def _constructor_expanddim(self) -> type[EventSchedule]:
        return EventSchedule

    def get_session(self, identifier: str | int) -> Session:
        """Return a :class:`~endurancepy.core.Session` of this event.

        The returned session already knows its season, so ``session.load()`` can
        discover and download its files without re-specifying ``season``.
        """
        return Session(
            year=self.year,
            series=self.series,
            event=str(self["EventFolder"]),
            name=str(identifier),
            default_season=self["Season"],
        )

    def get_race(self) -> Session:
        """Return the race session of this event."""
        return self.get_session("Race")

    def get_sessions(self) -> list[str]:
        """List this event's session names (e.g. practice / qualifying / race).

        Fetched on demand from the event's own portal page — the season
        calendar only lists the events, not the sessions inside each one.
        """
        from endurancepy.alkamel import discovery

        return discovery.fetch_event_sessions(
            self.series.host,
            str(self["Season"]),
            str(self["EventFolder"]),
            series_keyword=self.series.keyword,
        )


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
        Event name (fuzzy-matched at load time) or round number.
    session:
        Session name/abbreviation (e.g. ``"Race"``, ``"FP1"``, ``"Q"``).

    Returns
    -------
    Session
        An unloaded session object. Call :meth:`Session.load` to fetch data.
    """
    resolved = Series.coerce(series)
    return Session(year=year, series=resolved, event=event, name=str(session))


def get_event_schedule(
    year: int, series: str | Series, *, season: str | None = None
) -> EventSchedule:
    """Build the :class:`EventSchedule` for a season of a given series.

    Parameters
    ----------
    year:
        Season year. Used to auto-resolve the Al Kamel season id from the
        portal's season list (matched on the season's starting year).
    series:
        The championship.
    season:
        Al Kamel season id (e.g. ``"08_2018-2019"``) to use a specific season
        explicitly instead of resolving it from ``year``.
    """
    resolved = Series.coerce(series)
    from endurancepy.alkamel import discovery

    if season is None:
        season = _resolve_season(resolved, year)

    events = discovery.fetch_events(resolved.host, season)
    rows = [
        {
            "RoundNumber": event.round,
            "EventName": event.name,
            "EventFolder": event.event_folder,
            "EventDate": event.date,
            "Sessions": list(event.sessions),
            "Series": resolved.name,
            "Season": season,
        }
        for event in events
    ]
    frame = pd.DataFrame(rows, columns=list(_SCHEDULE_DTYPES))
    frame = frame.astype(_SCHEDULE_DTYPES)
    return EventSchedule(frame, year=year, series=resolved, season=season)


def get_event(
    year: int, series: str | Series, event: str | int, *, season: str | None = None
) -> Event:
    """Build the :class:`Event` best matching ``event`` in the season."""
    schedule = get_event_schedule(year, series, season=season)
    if isinstance(event, int):
        return schedule.get_event_by_round(event)
    return schedule.get_event_by_name(event)


def list_seasons(series: str | Series) -> list[str]:
    """Return the available Al Kamel season ids for a series (e.g. ``"13_2024"``).

    The id encodes the year(s): ``"13_2024"`` is 2024, ``"08_2018-2019"`` is the
    2018-2019 superseason.
    """
    resolved = Series.coerce(series)
    from endurancepy.alkamel import discovery

    return discovery.fetch_seasons(resolved.host)


def _resolve_season(series: Series, year: int) -> str:
    """Resolve a season id from a year by matching the season's starting year."""
    from endurancepy.alkamel import discovery

    seasons = discovery.fetch_seasons(series.host)
    for season_id in seasons:
        match = _SEASON_YEAR_RE.match(season_id)
        if match and int(match.group(1)) == year:
            return season_id
    raise SessionNotAvailableError(
        f"No {series.name} season starts in {year}. Available: {seasons}"
    )
