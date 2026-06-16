"""Plotting helpers, mirroring :mod:`fastf1.plotting`.

For endurance racing, colour helpers are organised by **class** and by
**manufacturer** rather than by driver. The colour lookups are pure functions
(they return hex strings and need no plotting backend); only :func:`setup_mpl`
requires matplotlib, which is provided by the optional ``plot`` extra
(``pip install endurancepy[plot]``).
"""

from __future__ import annotations

__all__ = [
    "DEFAULT_COLOR",
    "get_class_color",
    "get_manufacturer_color",
    "list_classes",
    "list_manufacturers",
    "setup_mpl",
]

#: Fallback colour for unknown classes/manufacturers.
DEFAULT_COLOR = "#777777"

#: Colour per racing class (keys are upper-cased on lookup).
CLASS_COLORS: dict[str, str] = {
    "HYPERCAR": "#E10600",
    "LMH": "#E10600",
    "LMDH": "#E10600",
    "GTP": "#00A19C",
    "LMP1": "#1F6FB2",
    "LMP2": "#0090D4",
    "LMP3": "#9B59B6",
    "LMGT3": "#2ECC71",
    "GT3": "#2ECC71",
    "GTD": "#27AE60",
    "GTD PRO": "#16A085",
    "GT": "#2ECC71",
    "LMGTE PRO": "#E67E22",
    "LMGTE AM": "#F1C40F",
    "DPI": "#8E44AD",
}

#: Colour per manufacturer (keys are upper-cased on lookup).
MANUFACTURER_COLORS: dict[str, str] = {
    "TOYOTA": "#EB0A1E",
    "FERRARI": "#DC0000",
    "PORSCHE": "#C9A227",
    "CADILLAC": "#941A1D",
    "BMW": "#0066B1",
    "PEUGEOT": "#1C3A5E",
    "ALPINE": "#1F6FB2",
    "ASTON MARTIN": "#00665E",
    "LAMBORGHINI": "#DDB321",
    "ACURA": "#C8102E",
    "MCLAREN": "#FF8000",
    "MERCEDES": "#27A2A2",
    "MERCEDES-AMG": "#27A2A2",
    "AUDI": "#BB0A30",
    "CHEVROLET": "#C5B358",
    "CORVETTE": "#C5B358",
    "FORD": "#00274C",
    "LEXUS": "#1A1A1A",
}


def get_class_color(class_name: str) -> str:
    """Return the hex colour for a racing class (case-insensitive)."""
    return CLASS_COLORS.get(str(class_name).strip().upper(), DEFAULT_COLOR)


def get_manufacturer_color(name: str) -> str:
    """Return the hex colour for a manufacturer (case-insensitive)."""
    return MANUFACTURER_COLORS.get(str(name).strip().upper(), DEFAULT_COLOR)


def list_classes() -> list[str]:
    """Return the known class names."""
    return list(CLASS_COLORS)


def list_manufacturers() -> list[str]:
    """Return the known manufacturer names."""
    return list(MANUFACTURER_COLORS)


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
