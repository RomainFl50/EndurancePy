"""Static-backend styling helpers (matplotlib / seaborn).

These cover the *static* "pretty" path (publication / PDF figures and statistical
distributions). The interactive charts live in :mod:`endurancepy.plotting.charts`
(Plotly). Matplotlib is the optional ``plot`` extra (``pip install
endurancepy[plot]``).
"""

from __future__ import annotations

__all__ = ["setup_mpl"]


def setup_mpl() -> None:
    """Apply EndurancePy's default matplotlib styling.

    Requires the optional ``plot`` extra (matplotlib).
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
