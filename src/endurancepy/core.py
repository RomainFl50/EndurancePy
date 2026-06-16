"""Core data objects: Session, Laps/Lap, SessionResults/CarResult.

These mirror FastF1's ``core`` module. The class structure and public method
signatures are defined here; the actual data loading and parsing land in later
milestones (2.1+) and currently raise :class:`NotImplementedError`.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING, Any

import pandas as pd

from endurancepy.exceptions import DataNotLoadedError

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
    ):
        self.year = year
        self.series = series
        self.event = event
        self.name = name
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
    ) -> None:
        """Download and parse the session's data from the Al Kamel archives.

        Not implemented yet (milestone 2.1+).
        """
        raise NotImplementedError

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
        """Track/flag status timeline. Available after :meth:`load`."""
        if self._track_status is None:
            raise DataNotLoadedError(
                "Track status is not loaded; call Session.load() first."
            )
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
