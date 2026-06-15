"""Core data objects: Session, Laps/Lap, SessionResults/CarResult.

These mirror FastF1's ``core`` module. The class structure and public method
signatures are defined here; the actual data loading and parsing land in later
milestones (2.1+) and currently raise :class:`NotImplementedError`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pandas as pd

from endurancepy.exceptions import DataNotLoadedError

if TYPE_CHECKING:
    from endurancepy.events import Series

__all__ = ["CarResult", "Lap", "Laps", "Session", "SessionResults"]


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
        """Return the laps driven by one or more drivers."""
        raise NotImplementedError

    def pick_teams(self, names: Any) -> Laps:
        """Return the laps of one or more teams."""
        raise NotImplementedError

    def pick_laps(self, lap_numbers: Any) -> Laps:
        """Return laps matching one or more lap numbers."""
        raise NotImplementedError

    def pick_fastest(self, only_by_time: bool = False) -> Lap | None:
        """Return the fastest lap, or ``None`` if there is none."""
        raise NotImplementedError

    def pick_quicklaps(self, threshold: float | None = None) -> Laps:
        """Return laps quicker than ``threshold`` times the best lap time."""
        raise NotImplementedError

    def pick_track_status(self, status: str, how: str = "equals") -> Laps:
        """Return laps set under a given track status."""
        raise NotImplementedError

    def pick_wo_box(self) -> Laps:
        """Return laps that are neither in-laps nor out-laps."""
        raise NotImplementedError

    def pick_box_laps(self, which: str = "both") -> Laps:
        """Return in-laps and/or out-laps."""
        raise NotImplementedError

    def pick_accurate(self) -> Laps:
        """Return laps that pass the accuracy validation check."""
        raise NotImplementedError

    # -- filtering (endurance additions) ------------------------------------
    def pick_cars(self, numbers: Any) -> Laps:
        """Return the laps of one or more cars (by car number)."""
        raise NotImplementedError

    def pick_classes(self, classes: Any) -> Laps:
        """Return the laps of one or more classes (e.g. ``"HYPERCAR"``)."""
        raise NotImplementedError

    def pick_manufacturers(self, names: Any) -> Laps:
        """Return the laps of one or more manufacturers."""
        raise NotImplementedError

    def pick_stints(self, numbers: Any) -> Laps:
        """Return the laps belonging to one or more stints."""
        raise NotImplementedError


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

    @property
    def _constructor(self) -> type[SessionResults]:
        return SessionResults

    @property
    def _constructor_sliced(self) -> type[CarResult]:
        return CarResult

    def pick_classes(self, classes: Any) -> SessionResults:
        """Return the results restricted to one or more classes."""
        raise NotImplementedError


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
        """Session classification. Available after :meth:`load`."""
        if self._results is None:
            raise DataNotLoadedError(
                "Results are not loaded; call Session.load() first."
            )
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
        """Car numbers that took part in the session (endurance equivalent of
        FastF1's ``Session.drivers``). Available after :meth:`load`."""
        raise NotImplementedError

    def get_car(self, number: str) -> CarResult:
        """Return the :class:`CarResult` for a given car number."""
        raise NotImplementedError
