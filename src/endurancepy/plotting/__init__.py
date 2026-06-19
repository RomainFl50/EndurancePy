"""Plotting helpers for EndurancePy, mirroring :mod:`fastf1.plotting`.

Two paths, by design (see ``ROADMAP.md``):

- **Interactive (Plotly)** — the dense, signature charts (:func:`plot_strategy`,
  more to come), where zoom/hover/legend-toggle keep a large field readable.
- **Static (matplotlib/seaborn)** — :func:`setup_mpl` styling for publication
  figures and statistical distributions.

Colours are organised by **class** and **manufacturer** (endurance has no
per-driver colours). Heavy backends are optional extras: ``endurancepy[plot]``
(matplotlib) and ``endurancepy[interactive]`` (plotly).
"""

from __future__ import annotations

from endurancepy.plotting.charts import plot_strategy
from endurancepy.plotting.colors import (
    CLASS_COLORS,
    DEFAULT_COLOR,
    MANUFACTURER_COLORS,
    get_class_color,
    get_manufacturer_color,
    list_classes,
    list_manufacturers,
)
from endurancepy.plotting.style import setup_mpl

__all__ = [
    "CLASS_COLORS",
    "DEFAULT_COLOR",
    "MANUFACTURER_COLORS",
    "get_class_color",
    "get_manufacturer_color",
    "list_classes",
    "list_manufacturers",
    "plot_strategy",
    "setup_mpl",
]
