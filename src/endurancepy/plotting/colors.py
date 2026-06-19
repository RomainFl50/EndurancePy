"""Colour registries for plotting, organised by **class** and **manufacturer**.

For endurance racing, colours are keyed by racing class (Hypercar / LMP2 /
LMGT3…) and by manufacturer rather than by driver. These lookups are pure
functions returning hex strings and need no plotting backend.
"""

from __future__ import annotations

__all__ = [
    "DEFAULT_COLOR",
    "get_car_style",
    "get_class_color",
    "get_manufacturer_color",
    "get_team_color",
    "list_classes",
    "list_manufacturers",
    "list_teams",
]

#: Line dashes / marker symbols cycled to tell apart cars sharing a class colour.
_DASHES = ("solid", "dash", "dot", "dashdot")
_SYMBOLS = ("circle", "square", "diamond", "triangle-up", "x", "star", "hexagon")

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


#: Colour per team, keyed by a distinctive **substring** of the entrant name
#: (entrant names vary a lot — "Ferrari AF Corse #51", "AF Corse" — so a
#: containment match is more robust than an exact one). Insertion order matters
#: when several keys could match.
TEAM_COLORS: dict[str, str] = {
    "TOYOTA GAZOO": "#EB0A1E",
    "AF CORSE": "#DC0000",
    "PORSCHE PENSKE": "#C9A227",
    "PENSKE": "#C9A227",
    "JOTA": "#1FA82C",
    "CADILLAC": "#941A1D",
    "BMW M TEAM WRT": "#0066B1",
    "WRT": "#0066B1",
    "PEUGEOT": "#1C3A5E",
    "ALPINE": "#005BA9",
    "ASTON MARTIN": "#00665E",
    "LAMBORGHINI": "#DDB321",
    "UNITED AUTOSPORTS": "#FF7F0E",
    "IRON DAMES": "#E75480",
    "IRON LYNX": "#1A1A1A",
    "CORVETTE": "#C5B358",
    "PROTON": "#E2001A",
}


def get_team_color(name: str) -> str:
    """Return the hex colour for a team (matched on a distinctive substring).

    Case-insensitive; returns :data:`DEFAULT_COLOR` when nothing matches.
    """
    upper = str(name).upper()
    for key, color in TEAM_COLORS.items():
        if key in upper:
            return color
    return DEFAULT_COLOR


def list_teams() -> list[str]:
    """Return the known team keys."""
    return list(TEAM_COLORS)


def get_car_style(car: str, class_name: str | None = None) -> dict[str, str]:
    """Return a per-car plotting style: ``{"color", "dash", "symbol"}``.

    The colour comes from the car's class (so a class reads as one colour); the
    dash and marker symbol are cycled deterministically from the car number, so
    the several cars sharing a class colour stay distinguishable (and readable in
    black & white). Stable across calls and runs.
    """
    color = get_class_color(class_name) if class_name is not None else DEFAULT_COLOR
    text = str(car)
    key = int(text) if text.isdigit() else abs(hash(text))
    return {
        "color": color,
        "dash": _DASHES[key % len(_DASHES)],
        "symbol": _SYMBOLS[key % len(_SYMBOLS)],
    }
