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

from endurancepy.plotting.charts import (
    add_track_status,
    plot_driver_comparison,
    plot_fastest_laps,
    plot_gap,
    plot_lap_evolution,
    plot_pace,
    plot_position_evolution,
    plot_race_trace,
    plot_stint_pace,
    plot_strategy,
    plot_top_speeds,
)
from endurancepy.plotting.colors import (
    CLASS_COLORS,
    DEFAULT_COLOR,
    MANUFACTURER_COLORS,
    TEAM_COLORS,
    get_car_style,
    get_class_color,
    get_manufacturer_color,
    get_team_color,
    list_classes,
    list_manufacturers,
    list_teams,
)
from endurancepy.plotting.style import format_time_axis, laptime_formatter, setup_mpl

__all__ = [
    "CLASS_COLORS",
    "DEFAULT_COLOR",
    "MANUFACTURER_COLORS",
    "TEAM_COLORS",
    "add_track_status",
    "format_time_axis",
    "get_car_style",
    "get_class_color",
    "get_manufacturer_color",
    "get_team_color",
    "laptime_formatter",
    "list_classes",
    "list_manufacturers",
    "list_teams",
    "plot_driver_comparison",
    "plot_fastest_laps",
    "plot_gap",
    "plot_lap_evolution",
    "plot_pace",
    "plot_position_evolution",
    "plot_race_trace",
    "plot_stint_pace",
    "plot_strategy",
    "plot_top_speeds",
    "setup_mpl",
]
