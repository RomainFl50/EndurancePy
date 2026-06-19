"""Static-backend styling helpers (matplotlib / seaborn).

These cover the *static* "pretty" path (publication / PDF figures and statistical
distributions). The interactive charts live in :mod:`endurancepy.plotting.charts`
(Plotly). Matplotlib is the optional ``plot`` extra (``pip install
endurancepy[plot]``).
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from endurancepy.utils import format_timedelta

__all__ = ["format_time_axis", "laptime_formatter", "setup_mpl"]

#: rcParams applied on top of the base ones for the dark theme.
_DARK_RCPARAMS: dict[str, Any] = {
    "figure.facecolor": "#111418",
    "axes.facecolor": "#111418",
    "savefig.facecolor": "#111418",
    "axes.edgecolor": "#AAAAAA",
    "axes.labelcolor": "#EEEEEE",
    "text.color": "#EEEEEE",
    "xtick.color": "#CCCCCC",
    "ytick.color": "#CCCCCC",
    "grid.color": "#444444",
}


def setup_mpl(theme: str = "light") -> None:
    """Apply EndurancePy's default matplotlib styling.

    ``theme`` is ``"light"`` (default) or ``"dark"``. Requires the optional
    ``plot`` extra (matplotlib).
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:  # pragma: no cover - depends on optional extra
        raise ImportError(
            "matplotlib is required for setup_mpl(); install endurancepy[plot]."
        ) from exc

    plt.rcParams["figure.figsize"] = (10.0, 5.0)
    plt.rcParams["axes.grid"] = True
    plt.rcParams["grid.alpha"] = 0.3
    plt.rcParams["legend.frameon"] = False
    if theme == "dark":
        plt.rcParams.update(_DARK_RCPARAMS)  # type: ignore[arg-type]


def laptime_formatter() -> Any:
    """A matplotlib tick formatter rendering an axis of *seconds* as ``M:SS.mmm``.

    Use on an axis whose values are lap/sector times in seconds (e.g. a seaborn
    box of ``LapTime.dt.total_seconds()``). Requires the ``plot`` extra.
    """
    try:
        from matplotlib.ticker import FuncFormatter
    except ImportError as exc:  # pragma: no cover - depends on optional extra
        raise ImportError(
            "matplotlib is required for laptime_formatter(); install endurancepy[plot]."
        ) from exc

    return FuncFormatter(
        lambda seconds, _pos: format_timedelta(pd.Timedelta(seconds=seconds))
    )


def format_time_axis(ax: Any, axis: str = "y") -> Any:
    """Format ``ax``'s ``"x"`` or ``"y"`` (seconds) as ``M:SS.mmm``; returns ``ax``."""
    target = ax.yaxis if axis == "y" else ax.xaxis
    target.set_major_formatter(laptime_formatter())
    return ax
