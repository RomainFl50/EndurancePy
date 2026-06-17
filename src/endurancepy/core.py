"""Core data objects: Session, Laps/Lap, SessionResults/CarResult.

These mirror FastF1's ``core`` module. :meth:`Session.load` reads an Analysis
CSV (from a path, bytes or URL) into :attr:`Session.laps`; results and track
status are derived from the laps on access. Automatic discovery of remote files
and the weather/race-control parsers are not implemented yet.
"""

from __future__ import annotations

import os
from collections.abc import Iterable
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pandas as pd

from endurancepy.cache import Cache
from endurancepy.exceptions import DataNotLoadedError, SessionNotAvailableError
from endurancepy.logger import LOGGER

if TYPE_CHECKING:
    from endurancepy.events import Series

__all__ = ["CarResult", "Lap", "Laps", "Session", "SessionResults"]


def _to_list(value: Any) -> list[Any]:
    """Wrap a scalar in a list; pass through (non-string) iterables as a list."""
    if isinstance(value, str) or not isinstance(value, Iterable):
        return [value]
    return list(value)


class Laps(pd.DataFrame):
    """A table of laps (one row per car-lap), as a pandas ``DataFrame`` subclass.

    Adds endurance-aware ``pick_*`` filtering helpers on top of normal DataFrame
    functionality. Slicing a single row yields a :class:`Lap`.
    """

    _metadata = ["session"]

    #: Threshold used by :meth:`pick_quicklaps` (defaults to the 107% rule).
    QUICKLAP_THRESHOLD: float = 1.07

    def __init__(self, *args: Any, session: Session | None = None, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.session = session

    @property
    def _constructor(self) -> type[Laps]:
        return Laps

    @property
    def _constructor_sliced(self) -> type[Lap]:
        return Lap

    # -- filtering (FastF1 parity) ------------------------------------------
    def pick_drivers(self, identifiers: Any) -> Laps:
        """Return the laps of one or more drivers (by number or name)."""
        ids = [str(i) for i in _to_list(identifiers)]
        mask = self["DriverNumber"].isin(ids) | self["Driver"].isin(ids)
        return self[mask]

    def pick_teams(self, names: Any) -> Laps:
        """Return the laps of one or more teams."""
        return self[self["Team"].isin([str(n) for n in _to_list(names)])]

    def pick_laps(self, lap_numbers: Any) -> Laps:
        """Return laps matching one or more lap numbers."""
        nums = [int(n) for n in _to_list(lap_numbers)]
        return self[self["LapNumber"].isin(nums)]

    def pick_fastest(self, only_by_time: bool = False) -> Lap | None:
        """Return the fastest lap, or ``None`` if there is none.

        By default only laps flagged as a personal best are considered (a faster
        lap not marked best was likely deleted). With ``only_by_time=True`` the
        lowest lap time is returned outright.
        """
        candidates = self if only_by_time else self[self._truthy("IsPersonalBest")]
        candidates = candidates[candidates["LapTime"].notna()]
        if len(candidates) == 0:
            return None
        return candidates.loc[candidates["LapTime"].idxmin()]

    def pick_quicklaps(self, threshold: float | None = None) -> Laps:
        """Return laps quicker than ``threshold`` times the best lap time."""
        coefficient = self.QUICKLAP_THRESHOLD if threshold is None else threshold
        fastest = self["LapTime"].min()
        if pd.isna(fastest):
            return self.iloc[0:0]
        return self[self["LapTime"] <= fastest * coefficient]

    def pick_track_status(self, status: str, how: str = "equals") -> Laps:
        """Return laps set under a given track status (e.g. ``"GF"``, ``"FCY"``)."""
        values = self["TrackStatus"].fillna("")
        if how == "equals":
            mask = values == status
        elif how == "contains":
            mask = values.str.contains(status, regex=False)
        elif how == "excludes":
            mask = ~values.str.contains(status, regex=False)
        elif how == "any":
            mask = values.apply(lambda v: any(c in v for c in status))
        elif how == "none":
            mask = values.apply(lambda v: not any(c in v for c in status))
        else:
            raise ValueError(f"Invalid value for 'how': {how!r}")
        return self[mask]

    def pick_wo_box(self) -> Laps:
        """Return laps that are neither in-laps nor out-laps."""
        return self[self["PitInTime"].isna() & self["PitOutTime"].isna()]

    def pick_box_laps(self, which: str = "both") -> Laps:
        """Return in-laps (``"in"``), out-laps (``"out"``) or both."""
        if which == "in":
            mask = self["PitInTime"].notna()
        elif which == "out":
            mask = self["PitOutTime"].notna()
        elif which == "both":
            mask = self["PitInTime"].notna() | self["PitOutTime"].notna()
        else:
            raise ValueError(f"Invalid value for 'which': {which!r}")
        return self[mask]

    def pick_accurate(self) -> Laps:
        """Return laps that pass the accuracy validation check."""
        return self[self._truthy("IsAccurate")]

    # -- filtering (endurance additions) ------------------------------------
    def pick_cars(self, numbers: Any) -> Laps:
        """Return the laps of one or more cars (by car number)."""
        return self[self["CarNumber"].isin([str(n) for n in _to_list(numbers)])]

    def pick_classes(self, classes: Any) -> Laps:
        """Return the laps of one or more classes (e.g. ``"HYPERCAR"``)."""
        values = [str(c).upper() for c in _to_list(classes)]
        return self[self["Class"].str.upper().isin(values)]

    def pick_manufacturers(self, names: Any) -> Laps:
        """Return the laps of one or more manufacturers."""
        values = [str(n).upper() for n in _to_list(names)]
        return self[self["Manufacturer"].str.upper().isin(values)]

    def pick_stints(self, numbers: Any) -> Laps:
        """Return the laps belonging to one or more stints."""
        return self[self["Stint"].isin([float(n) for n in _to_list(numbers)])]

    def _truthy(self, column: str) -> pd.Series:
        """Boolean mask for a nullable-boolean column (``NA`` treated as False)."""
        return self[column].fillna(False).astype(bool)


class Lap(pd.Series):
    """A single lap, as a pandas ``Series`` subclass."""

    _metadata = ["session"]

    @property
    def _constructor(self) -> type[Lap]:
        return Lap

    @property
    def _constructor_expanddim(self) -> type[Laps]:
        return Laps


class SessionResults(pd.DataFrame):
    """Classification for a session (one row per car/crew), per overall and class."""

    _metadata = ["session"]

    def __init__(self, *args: Any, session: Session | None = None, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.session = session

    @property
    def _constructor(self) -> type[SessionResults]:
        return SessionResults

    @property
    def _constructor_sliced(self) -> type[CarResult]:
        return CarResult

    def pick_classes(self, classes: Any) -> SessionResults:
        """Return the results restricted to one or more classes."""
        values = [str(c).upper() for c in _to_list(classes)]
        return self[self["Class"].str.upper().isin(values)]


class CarResult(pd.Series):
    """The result of a single car/crew, as a pandas ``Series`` subclass."""

    _metadata = ["session"]

    @property
    def _constructor(self) -> type[CarResult]:
        return CarResult

    @property
    def _constructor_expanddim(self) -> type[SessionResults]:
        return SessionResults


class Session:
    """Entry point for accessing the data of a single endurance session.

    A ``Session`` is normally created via :func:`endurancepy.get_session`. Most
    data is only available after calling :meth:`load`.
    """

    def __init__(
        self,
        year: int,
        series: Series,
        event: str | int,
        name: str,
        default_season: str | None = None,
    ):
        self.year = year
        self.series = series
        self.event = event
        self.name = name
        self.default_season = default_season
        self._laps: Laps | None = None
        self._results: SessionResults | None = None
        self._weather_data: pd.DataFrame | None = None
        self._track_status: pd.DataFrame | None = None

    def __repr__(self) -> str:
        return f"<Session {self.year} {self.series} {self.event!r} - {self.name}>"

    def load(
        self,
        *,
        laps: bool = True,
        weather: bool = True,
        messages: bool = True,
        source: bytes | str | os.PathLike[str] | None = None,
        weather_source: bytes | str | os.PathLike[str] | None = None,
        results_source: bytes | str | os.PathLike[str] | None = None,
        season: str | None = None,
    ) -> None:
        """Load the session's data.

        Parameters
        ----------
        laps:
            Load lap data. ``results`` and ``track_status`` are derived from it
            on access unless an explicit ``results_source`` is given.
        weather:
            Load weather data (from ``weather_source`` or via ``season``).
        messages:
            Accepted for FastF1 API compatibility; not loaded yet.
        source:
            Analysis CSV to read laps from: raw ``bytes``, a filesystem path, or
            an ``http(s)`` URL. When omitted, the parsed laps are loaded from the
            cache if present.
        weather_source:
            Optional Weather CSV (``bytes`` / path / URL) for ``weather_data``.
        results_source:
            Optional Classification CSV (``bytes`` / path / URL) for ``results``.
            When omitted, results are derived from the laps.
        season:
            Al Kamel season id (e.g. ``"08_2018-2019"``). When given, the event's
            files are discovered from the portal and downloaded automatically
            (the event/session are fuzzy-matched against this session's names).

        Raises
        ------
        SessionNotAvailableError
            If ``source`` is omitted and the laps are not in the cache.
        """
        season = season if season is not None else self.default_season
        if season is not None:
            self._load_via_discovery(season, laps=laps, weather=weather)
            return
        if weather and weather_source is not None:
            from endurancepy.alkamel.weather import read_weather

            self._weather_data = read_weather(self._read_source(weather_source))
        if laps:
            self._load_laps(source)
        if results_source is not None:
            from endurancepy.alkamel.classification import read_classification

            self._results = read_classification(
                self._read_source(results_source), session=self
            )

    def _load_laps(self, source: bytes | str | os.PathLike[str] | None) -> None:
        key = self._cache_key()
        if source is None:
            cached = Cache.load_dataframe(key)
            if cached is not None:
                self._laps = Laps(cached, session=self)
                self._results = None
                self._track_status = None
                return
            raise SessionNotAvailableError(
                "No laps in cache. Pass source=<path|bytes|url> or season=<id> to "
                "Session.load(), or parse a file directly with "
                "endurancepy.alkamel.analysis.read_analysis()."
            )
        from endurancepy.alkamel.analysis import read_analysis

        data = self._read_source(source)
        self._laps = read_analysis(data, session=self)
        self._results = None
        self._track_status = None
        Cache.save_dataframe(key, pd.DataFrame(self._laps))

    def _load_via_discovery(self, season: str, *, laps: bool, weather: bool) -> None:
        from endurancepy.alkamel import discovery
        from endurancepy.alkamel.analysis import read_analysis
        from endurancepy.alkamel.classification import read_classification
        from endurancepy.alkamel.client import download
        from endurancepy.alkamel.weather import read_weather

        host = self.series.host
        LOGGER.info(
            "Loading %s %s '%s' %s (season %s)",
            self.series.name,
            self.year,
            self.event,
            self.name,
            season,
        )
        event = discovery.find_event(
            discovery.fetch_events(host, season), str(self.event)
        )
        LOGGER.info("Matched event '%s' -> %s", self.event, event.event_folder)
        records = discovery.fetch_index(host, season, event=event.event_folder)
        files = discovery.resolve_session_files(
            records,
            event=event.name,
            session=self.name,
            series_keyword=self.series.keyword,
        )
        LOGGER.info(
            "Resolved files: %s",
            ", ".join(f"{kind}={rf.filename}" for kind, rf in files.items()) or "none",
        )
        if laps and "analysis" in files:
            self._laps = read_analysis(
                download(files["analysis"].url(host)), session=self
            )
            self._results = None
            self._track_status = None
            LOGGER.info("Parsed %d laps", len(self._laps))
            Cache.save_dataframe(self._cache_key(), pd.DataFrame(self._laps))
        if "classification" in files:
            self._results = read_classification(
                download(files["classification"].url(host)), session=self
            )
        if weather and "weather" in files:
            self._weather_data = read_weather(download(files["weather"].url(host)))

    def _cache_key(self) -> str:
        def safe(value: object) -> str:
            return str(value).strip().replace("/", "-").replace(" ", "_")

        return (
            f"{self.series.name}/{self.year}/{safe(self.event)}/{safe(self.name)}/laps"
        )

    @staticmethod
    def _read_source(source: bytes | str | os.PathLike[str]) -> bytes:
        if isinstance(source, (bytes, bytearray)):
            return bytes(source)
        text = str(source)
        if text.startswith(("http://", "https://")):
            from endurancepy.alkamel.client import download

            return download(text)
        return Path(source).read_bytes()

    @property
    def laps(self) -> Laps:
        """All laps of the session. Available after :meth:`load`."""
        if self._laps is None:
            raise DataNotLoadedError("Laps are not loaded; call Session.load() first.")
        return self._laps

    @property
    def results(self) -> SessionResults:
        """Session classification (per car & per class).

        Derived from :attr:`laps` (final order by laps then total time) when not
        provided directly. Available once lap data is loaded.
        """
        if self._results is None:
            if self._laps is None:
                raise DataNotLoadedError(
                    "Results are not loaded; call Session.load() first."
                )
            from endurancepy.results import from_laps

            self._results = from_laps(self._laps, session=self)
        return self._results

    @property
    def weather_data(self) -> pd.DataFrame:
        """Weather data. Available after ``load(weather=True)``."""
        if self._weather_data is None:
            raise DataNotLoadedError(
                "Weather data is not loaded; call Session.load() first."
            )
        return self._weather_data

    @property
    def track_status(self) -> pd.DataFrame:
        """Track/flag status timeline (green / FCY / SC / code 60 / red).

        Derived from the laps' finish-line flags when not provided directly.
        Available once lap data is loaded.
        """
        if self._track_status is None:
            if self._laps is None:
                raise DataNotLoadedError(
                    "Track status is not loaded; call Session.load() first."
                )
            from endurancepy.track_status import from_laps

            self._track_status = from_laps(self._laps)
        return self._track_status

    @property
    def cars(self) -> list[str]:
        """Car numbers that took part, in finishing order (endurance equivalent
        of FastF1's ``Session.drivers``). Available once lap data is loaded."""
        return [str(number) for number in self.results["CarNumber"].tolist()]

    def get_car(self, number: str) -> CarResult:
        """Return the :class:`CarResult` for a given car number."""
        results = self.results
        match = results[results["CarNumber"] == str(number)]
        if len(match) == 0:
            raise ValueError(f"No car {number!r} in this session")
        return match.iloc[0]
