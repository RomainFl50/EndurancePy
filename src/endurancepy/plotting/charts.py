"""Interactive chart builders (Plotly).

Endurance fields are large (30-60+ cars) and races are long (hundreds of laps),
so a static chart of the whole field quickly turns into spaghetti. These helpers
return interactive :class:`plotly.graph_objects.Figure` objects — zoom into a
stint, hover for the details, click the legend to isolate a class — instead of a
flat image.

Plotly is an optional dependency: ``pip install endurancepy[interactive]``. Each
helper returns the native Plotly figure so callers can keep customising it (then
``fig.show()`` / ``fig.write_html(...)``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pandas as pd

from endurancepy.plotting.colors import get_class_color

if TYPE_CHECKING:
    import plotly.graph_objects as go

__all__ = ["plot_strategy"]


def _import_go() -> Any:
    """Import ``plotly.graph_objects`` or raise a helpful error."""
    try:
        import plotly.graph_objects as go
    except ImportError as exc:  # pragma: no cover - depends on optional extra
        raise ImportError(
            "plotly is required for interactive charts; "
            "install endurancepy[interactive]."
        ) from exc
    return go


def _laps_frame(source: Any) -> pd.DataFrame:
    """Accept a Session (use its ``laps``) or a Laps/DataFrame directly."""
    laps = getattr(source, "laps", source)
    return pd.DataFrame(laps)


def _car_sort_key(car: str) -> tuple[int, Any]:
    """Sort car numbers numerically when possible, else lexically."""
    text = str(car)
    return (0, int(text)) if text.isdigit() else (1, text)


def plot_strategy(source: Any, *, title: str = "Race strategy") -> go.Figure:
    """Stint / strategy chart: one bar per stint, per car, coloured by class.

    Parameters
    ----------
    source:
        A loaded :class:`~endurancepy.core.Session` or a
        :class:`~endurancepy.core.Laps` table.
    title:
        Figure title.

    Each car gets a horizontal bar per stint along the lap axis; the gaps between
    a car's bars are its pit stops. Bars are coloured by class (one legend entry
    per class, click to toggle) and the hover shows the stint's driver(s) and lap
    range. Returns a :class:`plotly.graph_objects.Figure`.
    """
    go = _import_go()
    frame = _laps_frame(source)
    if frame.empty or "Stint" not in frame:
        return go.Figure(layout={"title": title})

    # Collapse to one row per (car, stint): lap span, lap count, class, driver(s).
    stints = (
        frame.dropna(subset=["Stint"])
        .groupby(["CarNumber", "Stint"], sort=True)
        .agg(
            first=("LapNumber", "min"),
            last=("LapNumber", "max"),
            laps=("LapNumber", "size"),
            klass=("Class", "last"),
            drivers=(
                "Driver",
                lambda s: "; ".join(dict.fromkeys(s.dropna().astype(str))),
            ),
        )
        .reset_index()
    )

    # Order the car axis by class, then car number (top-down).
    car_class = stints.groupby("CarNumber")["klass"].last()
    cars = sorted(car_class.index, key=lambda c: (str(car_class[c]), _car_sort_key(c)))

    fig = go.Figure()
    for klass, rows in stints.groupby("klass", sort=True):
        first = rows["first"].astype(int)
        last = rows["last"].astype(int)
        customdata = list(
            zip(
                rows["Stint"].astype(int),
                rows["drivers"],
                rows["laps"].astype(int),
                first,
                last,
                strict=True,
            )
        )
        fig.add_bar(
            y=rows["CarNumber"],
            x=last - first + 1,  # bar length in laps
            base=first,  # first lap of the stint
            orientation="h",
            name=str(klass),
            legendgroup=str(klass),
            marker_color=get_class_color(str(klass)),
            customdata=customdata,
            hovertemplate=(
                "Car %{y} · %{fullData.name}<br>"
                "Stint %{customdata[0]} — laps %{customdata[3]}–%{customdata[4]} "
                "(%{customdata[2]})<br>"
                "%{customdata[1]}<extra></extra>"
            ),
        )

    fig.update_layout(
        title=title,
        barmode="overlay",
        xaxis_title="Lap number",
        yaxis_title="Car",
        legend_title="Class",
        height=max(320, 28 * len(cars) + 140),
    )
    fig.update_xaxes(rangemode="tozero")
    fig.update_yaxes(categoryorder="array", categoryarray=cars, autorange="reversed")
    return fig
