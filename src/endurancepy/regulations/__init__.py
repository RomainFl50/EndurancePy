"""Stored championship regulations (the machine-useful subset).

Endurance scoring and rules vary by **series and year** (points scales, the Le
Mans multiplier, pole/fastest-lap points, drop scores, tyre allocation...), and
they are not in the timing archives. This package keeps a small, curated,
**YAML** knowledge base of those rules so tools like
:func:`~endurancepy.compute_standings` can be series/season-accurate.

Design notes:

- We store our own machine-readable *extract*, never the copyrighted regulation
  PDFs. Every file records the **source URL(s)** it was built from (``sources``)
  so the data can be checked or extended later, and a ``status`` of ``verified``
  or ``approximate``.
- Scope today is **scoring** (points). The schema leaves room for pit / driver-
  time / tyre context. Per-stop tyre changes are *not* derivable (free choice of
  how many tyres to change, and not published in the timing) — regulations only
  give allocation context, never the per-stop gesture.
- It's just data: new series/seasons are added by dropping a YAML file in
  ``data/<SERIES>/<year>.yaml``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from importlib import resources
from typing import Any

from endurancepy.events import Series
from endurancepy.exceptions import RegulationsNotAvailableError

__all__ = [
    "PointsSystem",
    "Regulations",
    "Source",
    "list_regulations",
    "regulations",
]


@dataclass(frozen=True)
class Source:
    """A regulation document the data was extracted from."""

    title: str
    url: str


@dataclass(frozen=True)
class PointsSystem:
    """A championship's scoring rules."""

    race: tuple[float, ...]  # points for P1, P2, ... (per class when per_class)
    pole: float = 0.0
    fastest_lap: float = 0.0
    per_class: bool = True
    le_mans_multiplier: float = 1.0  # Le Mans points are scaled by this
    drop_scores: int = 0  # number of worst rounds dropped (0 = none)


@dataclass(frozen=True)
class Regulations:
    """The stored regulations for one series/season."""

    series: str
    season: int
    points: PointsSystem
    classes: tuple[str, ...] = ()
    tyres: dict[str, Any] = field(default_factory=dict)
    sources: tuple[Source, ...] = ()
    status: str = "approximate"  # "verified" | "approximate"


def _data_root() -> Any:
    return resources.files("endurancepy.regulations") / "data"


def regulations(series: str | Series, year: int) -> Regulations:
    """Return the stored :class:`Regulations` for a series and season.

    Raises :class:`~endurancepy.exceptions.RegulationsNotAvailableError` if no
    file is stored for that series/season (see :func:`list_regulations`).
    """
    resolved = Series.coerce(series)
    path = _data_root() / resolved.name / f"{year}.yaml"
    if not path.is_file():
        raise RegulationsNotAvailableError(
            f"No stored {resolved.name} regulations for {year}. "
            f"Available: {list_regulations(resolved)}"
        )
    return _parse(path.read_text(encoding="utf-8"))


def list_regulations(series: str | Series | None = None) -> list[tuple[str, int]]:
    """List the available ``(series, year)`` regulation files."""
    available: list[tuple[str, int]] = []
    only = Series.coerce(series).name if series is not None else None
    root = _data_root()
    for series_dir in root.iterdir():
        if not series_dir.is_dir() or (only is not None and series_dir.name != only):
            continue
        for entry in series_dir.iterdir():
            if entry.name.endswith(".yaml"):
                available.append((series_dir.name, int(entry.name[:-5])))
    return sorted(available)


def _parse(text: str) -> Regulations:
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError as exc:  # pragma: no cover - depends on optional dep
        raise ImportError(
            "PyYAML is required to read regulations; install endurancepy[regulations]."
        ) from exc

    data = yaml.safe_load(text)
    points = data["points"]
    return Regulations(
        series=str(data["series"]),
        season=int(data["season"]),
        points=PointsSystem(
            race=tuple(float(p) for p in points["race"]),
            pole=float(points.get("pole", 0.0)),
            fastest_lap=float(points.get("fastest_lap", 0.0)),
            per_class=bool(points.get("per_class", True)),
            le_mans_multiplier=float(points.get("le_mans_multiplier", 1.0)),
            drop_scores=int(points.get("drop_scores", 0)),
        ),
        classes=tuple(data.get("classes", ()) or ()),
        tyres=dict(data.get("tyres", {}) or {}),
        sources=tuple(
            Source(title=str(s["title"]), url=str(s["url"]))
            for s in data.get("sources", []) or []
        ),
        status=str(data.get("status", "approximate")),
    )
