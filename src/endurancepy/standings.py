"""Championship standings: a configurable points calculator.

There is no single, official points feed for endurance championships, and the
exact rules vary by series and year (bonus points, Le Mans multipliers, dropped
scores...). This module therefore provides a **generic, configurable** calculator
that aggregates points from a season's session results, not a hard-coded replica
of any one championship's regulations.

Example::

    rounds = [race1.results, race2.results, ...]
    table = ep.compute_standings(rounds, by="CarNumber", per_class=True)
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import TYPE_CHECKING, Any

import pandas as pd

if TYPE_CHECKING:
    from endurancepy.regulations import Regulations

__all__ = ["POINTS_SYSTEMS", "Standings", "compute_standings"]

#: Named points systems (index 0 = points for P1). Extend or pass your own.
POINTS_SYSTEMS: dict[str, list[float]] = {
    # Generic FIA-style top-10 table; a reasonable default, not series-official.
    "default": [25, 18, 15, 12, 10, 8, 6, 4, 2, 1],
    "fia_top10": [25, 18, 15, 12, 10, 8, 6, 4, 2, 1],
}


class Standings(pd.DataFrame):
    """Championship standings table (a pandas ``DataFrame`` subclass)."""

    @property
    def _constructor(self) -> type[Standings]:
        return Standings


def _resolve_points(
    points: str | Sequence[float] | dict[int, float] | None,
) -> list[float]:
    if points is None:
        points = "default"
    if isinstance(points, str):
        if points not in POINTS_SYSTEMS:
            raise KeyError(f"Unknown points system {points!r}.")
        return list(POINTS_SYSTEMS[points])
    if isinstance(points, dict):
        highest = max(points) if points else 0
        return [float(points.get(i + 1, 0)) for i in range(highest)]
    return [float(p) for p in points]


def _points_for(position: Any, table: list[float]) -> float:
    if position is None or pd.isna(position):
        return 0.0
    index = int(position) - 1
    return table[index] if 0 <= index < len(table) else 0.0


def compute_standings(
    results: Iterable[pd.DataFrame],
    *,
    points: str | Sequence[float] | dict[int, float] | None = None,
    by: str = "CarNumber",
    per_class: bool | None = None,
    regulations: Regulations | None = None,
) -> Standings:
    """Aggregate championship standings from a sequence of session results.

    Parameters
    ----------
    results:
        One ``SessionResults`` (or DataFrame) per counting round.
    points:
        A named system (key of :data:`POINTS_SYSTEMS`), a sequence (P1 first), or
        a ``{position: points}`` mapping. Defaults to ``"default"``.
    by:
        Column identifying the entrant: ``"CarNumber"``, ``"Crew"``,
        ``"TeamName"`` or ``"Manufacturer"``.
    per_class:
        If true, award points by ``PositionInClass`` and rank within each class.
    regulations:
        Optional :class:`~endurancepy.regulations.Regulations` (e.g.
        ``ep.regulations("WEC", 2024)``): its points scale and per-class flag are
        used unless ``points`` / ``per_class`` are passed explicitly. (The Le Mans
        multiplier and drop scores it carries are not applied here yet — they need
        per-event context.)
    """
    if regulations is not None:
        if points is None:
            points = list(regulations.points.race)
        if per_class is None:
            per_class = regulations.points.per_class
    table = _resolve_points(points)
    per_class = bool(per_class)
    position_column = "PositionInClass" if per_class else "Position"

    aggregate: dict[tuple[Any, ...], dict[str, Any]] = {}
    for result in results:
        for _, row in result.iterrows():
            entrant = row.get(by)
            if entrant is None or pd.isna(entrant):
                continue
            position = row.get(position_column)
            class_name = row.get("Class") if per_class else None
            key = (entrant, class_name)
            record = aggregate.setdefault(
                key,
                {"Points": 0.0, "Wins": 0, "Events": 0, "Class": class_name},
            )
            record["Points"] += _points_for(position, table)
            record["Events"] += 1
            if position is not None and not pd.isna(position) and int(position) == 1:
                record["Wins"] += 1

    rows = []
    for (entrant, _class), record in aggregate.items():
        row_data: dict[str, Any] = {by: entrant}
        if per_class:
            row_data["Class"] = record["Class"]
        row_data["Points"] = record["Points"]
        row_data["Wins"] = record["Wins"]
        row_data["Events"] = record["Events"]
        rows.append(row_data)

    columns = [by, *(["Class"] if per_class else []), "Points", "Wins", "Events"]
    frame = pd.DataFrame(rows, columns=columns)
    frame = frame.sort_values(
        ["Points", "Wins", by], ascending=[False, False, True]
    ).reset_index(drop=True)

    if per_class:
        frame["Position"] = frame.groupby("Class", sort=False).cumcount() + 1
    else:
        frame["Position"] = frame.index + 1

    frame = frame.astype({"Points": "float64", "Wins": "int64", "Events": "int64"})
    return Standings(frame)
