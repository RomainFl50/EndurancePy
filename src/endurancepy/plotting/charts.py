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

from endurancepy.plotting.colors import get_car_style, get_class_color
from endurancepy.utils import format_timedelta

if TYPE_CHECKING:
    import plotly.graph_objects as go

__all__ = [
    "add_track_status",
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
]

#: Anchor a timedelta onto a clock so a Plotly date axis renders M:SS.mmm ticks.
_EPOCH = pd.Timestamp(0)

#: Non-green field states worth shading on a chart, with a colour and label.
_NEUTRAL_STATUS: dict[str, tuple[str, str]] = {
    "FCY": ("#F1C40F", "Full-course yellow"),
    "SC": ("#E67E22", "Safety car"),
    "C60": ("#F39C12", "Code 60"),
    "CODE60": ("#F39C12", "Code 60"),
    "SF": ("#F1C40F", "Slow zone"),
    "YEL": ("#F1C40F", "Yellow"),
    "RED": ("#E74C3C", "Red flag"),
    "FF": ("#9B59B6", "Chequered"),
}


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


def _prep(source: Any) -> pd.DataFrame:
    """Laps as a frame, sorted per car/lap (drops laps with no lap number)."""
    frame = _laps_frame(source)
    if frame.empty or "LapNumber" not in frame:
        return pd.DataFrame()
    return frame.dropna(subset=["LapNumber"]).sort_values(["CarNumber", "LapNumber"])


def _car_lines(
    fig: Any,
    frame: pd.DataFrame,
    ycol: str,
    *,
    mode: str,
    hovertemplate: str,
    customcols: tuple[str, ...] = (),
) -> None:
    """Add one line per car (colour by class, dash/marker by car), legend by class."""
    seen: set[str] = set()
    for car, g in frame.groupby("CarNumber", sort=True):
        klass = str(g["Class"].iloc[-1])
        style = get_car_style(str(car), klass)
        fig.add_scatter(
            x=g["LapNumber"],
            y=g[ycol],
            mode=mode,
            name=str(car),
            legendgroup=klass,
            legendgrouptitle_text=None if klass in seen else klass,
            line={"color": style["color"], "dash": style["dash"]},
            marker={"color": style["color"], "symbol": style["symbol"], "size": 6},
            customdata=g[list(customcols)].to_numpy() if customcols else None,
            hovertemplate=hovertemplate,
        )
        seen.add(klass)


def plot_lap_evolution(source: Any, *, title: str = "Lap-time evolution") -> go.Figure:
    """Lap time vs lap number, one line per car (colour by class).

    The y-axis is a clock (ticks read ``M:SS.mmm``). ``source`` is a Session or
    Laps. Returns a :class:`plotly.graph_objects.Figure`.
    """
    go = _import_go()
    fig = go.Figure(layout={"title": title})
    frame = _prep(source)
    if frame.empty:
        return fig
    frame = frame.dropna(subset=["LapTime"]).copy()
    frame["_clock"] = _EPOCH + frame["LapTime"]
    frame["_lap"] = frame["LapNumber"].astype(int)
    frame["_drv"] = frame["Driver"].fillna("")
    _car_lines(
        fig,
        frame,
        "_clock",
        mode="lines+markers",
        customcols=("_lap", "_drv"),
        hovertemplate=(
            "Car %{fullData.name}<br>Lap %{customdata[0]} · %{y|%M:%S.%L}<br>"
            "%{customdata[1]}<extra></extra>"
        ),
    )
    fig.update_layout(xaxis_title="Lap", yaxis_title="Lap time", legend_title="Class")
    fig.update_yaxes(tickformat="%M:%S.%L")
    return fig


def plot_pace(
    source: Any, *, kind: str = "box", title: str = "Pace by class"
) -> go.Figure:
    """Lap-time distribution per class (y-axis reads ``M:SS.mmm``).

    ``kind`` is ``"box"`` (default) or ``"violin"``.
    """
    go = _import_go()
    fig = go.Figure(layout={"title": title})
    frame = _prep(source)
    if frame.empty:
        return fig
    frame = frame.dropna(subset=["LapTime"])
    for klass in sorted(frame["Class"].dropna().unique()):
        rows = frame[frame["Class"] == klass]
        color = get_class_color(str(klass))
        if kind == "violin":
            fig.add_violin(
                y=_EPOCH + rows["LapTime"],
                name=str(klass),
                line_color=color,
                meanline_visible=True,
            )
        else:
            fig.add_box(y=_EPOCH + rows["LapTime"], name=str(klass), marker_color=color)
    fig.update_layout(xaxis_title="Class", yaxis_title="Lap time", showlegend=False)
    fig.update_yaxes(tickformat="%M:%S.%L")
    return fig


def plot_position_evolution(
    source: Any, *, in_class: bool = False, title: str | None = None
) -> go.Figure:
    """Position vs lap number, one line per car (P1 at the top)."""
    go = _import_go()
    column = "PositionInClass" if in_class else "Position"
    title = title or ("Class position" if in_class else "Overall position")
    fig = go.Figure(layout={"title": title})
    frame = _prep(source)
    if frame.empty:
        return fig
    frame = frame.dropna(subset=[column]).copy()
    frame["_pos"] = frame[column].astype(int)
    frame["_lap"] = frame["LapNumber"].astype(int)
    _car_lines(
        fig,
        frame,
        "_pos",
        mode="lines+markers",
        customcols=("_lap",),
        hovertemplate=(
            "Car %{fullData.name}<br>Lap %{customdata[0]} · P%{y}<extra></extra>"
        ),
    )
    fig.update_layout(xaxis_title="Lap", yaxis_title="Position", legend_title="Class")
    fig.update_yaxes(autorange="reversed", dtick=1)
    return fig


def plot_gap(
    source: Any, *, in_class: bool = False, title: str | None = None
) -> go.Figure:
    """Gap to the (class) leader in seconds vs lap number, one line per car."""
    go = _import_go()
    column = "GapToLeaderInClass" if in_class else "GapToLeader"
    title = title or ("Gap to class leader" if in_class else "Gap to leader")
    fig = go.Figure(layout={"title": title})
    frame = _prep(source)
    if frame.empty:
        return fig
    frame = frame.dropna(subset=[column]).copy()
    frame["_gap"] = frame[column].dt.total_seconds()
    frame["_lap"] = frame["LapNumber"].astype(int)
    _car_lines(
        fig,
        frame,
        "_gap",
        mode="lines",
        customcols=("_lap",),
        hovertemplate=(
            "Car %{fullData.name}<br>Lap %{customdata[0]} · +%{y:.1f}s<extra></extra>"
        ),
    )
    fig.update_layout(xaxis_title="Lap", yaxis_title="Gap (s)", legend_title="Class")
    fig.update_yaxes(autorange="reversed")  # leader (0) on top, behind goes down
    return fig


def plot_race_trace(source: Any, *, title: str = "Race trace") -> go.Figure:
    """Cumulative delta to a constant reference pace, one line per car.

    The reference is the field's median lap time; the y value is
    ``lap × reference − elapsed`` (seconds), so a rising line is gaining on the
    reference pace and a falling line is losing — isolating pace from the leader's
    own drift.
    """
    go = _import_go()
    fig = go.Figure(layout={"title": title})
    frame = _prep(source)
    if frame.empty:
        return fig
    frame = frame.dropna(subset=["Time", "LapTime"]).copy()
    reference = frame["LapTime"].median()
    ref_seconds = reference.total_seconds()
    frame["_trace"] = (
        frame["LapNumber"] * ref_seconds - frame["Time"].dt.total_seconds()
    )
    frame["_lap"] = frame["LapNumber"].astype(int)
    _car_lines(
        fig,
        frame,
        "_trace",
        mode="lines",
        customcols=("_lap",),
        hovertemplate=(
            "Car %{fullData.name}<br>Lap %{customdata[0]} · Δ%{y:.1f}s<extra></extra>"
        ),
    )
    fig.update_layout(
        xaxis_title="Lap",
        yaxis_title=f"Δ to {format_timedelta(reference)} ref pace (s)",
        legend_title="Class",
    )
    return fig


def add_track_status(fig: go.Figure, source: Any) -> go.Figure:
    """Shade the lap windows where the field ran under a neutralisation.

    Reads the per-lap ``TrackStatus`` (the field's most common flag each lap) and
    adds a coloured band for each contiguous run of FCY / safety car / code 60 /
    red flag, on the lap (x) axis. A no-op when no flags are present (e.g. older
    seasons). Returns ``fig`` for chaining.
    """
    frame = _laps_frame(source)
    if frame.empty or "TrackStatus" not in frame:
        return fig
    flags = frame.dropna(subset=["LapNumber", "TrackStatus"])
    if flags.empty:
        return fig

    def _mode(values: pd.Series) -> Any:
        common = values.mode()
        return common.iloc[0] if len(common) else None

    status = flags.groupby("LapNumber")["TrackStatus"].agg(_mode)
    runs: list[tuple[float, float, str]] = []
    current: tuple[float, float, str] | None = None
    for lap, raw in status.items():
        code = str(raw).strip().upper()
        if code in _NEUTRAL_STATUS:
            if current and current[2] == code:
                current = (current[0], float(lap), code)
            else:
                if current:
                    runs.append(current)
                current = (float(lap), float(lap), code)
        elif current:
            runs.append(current)
            current = None
    if current:
        runs.append(current)

    for start, end, code in runs:
        color, label = _NEUTRAL_STATUS[code]
        fig.add_vrect(
            x0=start - 0.5,
            x1=end + 0.5,
            fillcolor=color,
            opacity=0.15,
            line_width=0,
            layer="below",
            annotation_text=label,
            annotation_position="top left",
        )
    return fig


def plot_fastest_laps(source: Any, *, title: str = "Fastest lap per car") -> go.Figure:
    """Each car's best lap as a bar — the delta to the overall best, by class.

    Bars show how far off the quickest lap each car was (the quickest sits at the
    top with a zero-length bar); the hover gives the absolute lap time. Coloured
    by class.
    """
    go = _import_go()
    fig = go.Figure(layout={"title": title})
    frame = _laps_frame(source)
    if frame.empty or "LapTime" not in frame:
        return fig
    frame = frame.dropna(subset=["LapTime"])
    if frame.empty:
        return fig

    best = (
        frame.groupby("CarNumber")
        .agg(best=("LapTime", "min"), klass=("Class", "last"))
        .reset_index()
        .sort_values("best")
    )
    overall = best["best"].min()
    best["_delta"] = (best["best"] - overall).dt.total_seconds()
    best["_abs"] = best["best"].map(format_timedelta)
    cars = best["CarNumber"].tolist()

    for klass, rows in best.groupby("klass", sort=True):
        fig.add_bar(
            y=rows["CarNumber"],
            x=rows["_delta"],
            orientation="h",
            name=str(klass),
            legendgroup=str(klass),
            marker_color=get_class_color(str(klass)),
            customdata=rows["_abs"],
            hovertemplate=(
                "Car %{y} · %{fullData.name}<br>%{customdata} "
                "(+%{x:.3f}s)<extra></extra>"
            ),
        )
    fig.update_layout(
        xaxis_title="Gap to overall best (s)", yaxis_title="Car", legend_title="Class"
    )
    fig.update_yaxes(categoryorder="array", categoryarray=cars, autorange="reversed")
    return fig


def plot_stint_pace(
    source: Any, *, car: str | None = None, title: str | None = None
) -> go.Figure:
    """Lap time vs lap-in-stint, one line per stint — the degradation view.

    A line per ``(car, stint)`` against the lap number *within* the stint, so
    tyre/fuel degradation and out-laps are visible. Pass ``car`` to focus on a
    single car; otherwise the whole field is drawn (toggle classes in the legend).
    The y-axis reads ``M:SS.mmm``.
    """
    go = _import_go()
    title = title or (f"Stint pace — car {car}" if car else "Stint pace")
    fig = go.Figure(layout={"title": title})
    frame = _prep(source)
    if frame.empty:
        return fig
    frame = frame.dropna(subset=["LapTime", "Stint"])
    if car is not None:
        frame = frame[frame["CarNumber"].astype(str) == str(car)]
    if frame.empty:
        return fig
    frame = frame.copy()
    frame["_lis"] = (
        frame["LapNumber"]
        - frame.groupby(["CarNumber", "Stint"])["LapNumber"].transform("min")
        + 1
    ).astype(int)
    frame["_clock"] = _EPOCH + frame["LapTime"]

    seen: set[str] = set()
    for (this_car, stint), g in frame.groupby(["CarNumber", "Stint"], sort=True):
        klass = str(g["Class"].iloc[-1])
        style = get_car_style(str(this_car), klass)
        fig.add_scatter(
            x=g["_lis"],
            y=g["_clock"],
            mode="lines+markers",
            name=f"#{this_car} stint {int(stint)}",
            legendgroup=klass,
            legendgrouptitle_text=None if klass in seen else klass,
            line={"color": style["color"], "dash": style["dash"]},
            marker={"color": style["color"], "symbol": style["symbol"], "size": 6},
            hovertemplate=(
                "#%{fullData.name}<br>lap-in-stint %{x} · %{y|%M:%S.%L}<extra></extra>"
            ),
        )
        seen.add(klass)
    fig.update_layout(
        xaxis_title="Lap in stint", yaxis_title="Lap time", legend_title="Class"
    )
    fig.update_xaxes(dtick=1)
    fig.update_yaxes(tickformat="%M:%S.%L")
    return fig


def plot_driver_comparison(
    source: Any, car: str, *, kind: str = "box", title: str | None = None
) -> go.Figure:
    """Lap-time distribution per driver within one car's crew.

    ``kind`` is ``"box"`` (default) or ``"violin"``. The y-axis reads
    ``M:SS.mmm``.
    """
    go = _import_go()
    title = title or f"Car {car} — pace by driver"
    fig = go.Figure(layout={"title": title})
    frame = _laps_frame(source)
    if frame.empty or "LapTime" not in frame:
        return fig
    frame = frame[frame["CarNumber"].astype(str) == str(car)].dropna(
        subset=["LapTime", "Driver"]
    )
    if frame.empty:
        return fig
    color = get_class_color(str(frame["Class"].iloc[-1]))
    for driver in dict.fromkeys(frame["Driver"].astype(str)):
        laptimes = _EPOCH + frame.loc[frame["Driver"] == driver, "LapTime"]
        if kind == "violin":
            fig.add_violin(y=laptimes, name=driver, line_color=color)
        else:
            fig.add_box(y=laptimes, name=driver, marker_color=color)
    fig.update_layout(xaxis_title="Driver", yaxis_title="Lap time", showlegend=False)
    fig.update_yaxes(tickformat="%M:%S.%L")
    return fig


def plot_top_speeds(source: Any, *, title: str = "Top speed by class") -> go.Figure:
    """Top-speed (km/h) distribution as one box per class."""
    go = _import_go()
    fig = go.Figure(layout={"title": title})
    frame = _laps_frame(source)
    if frame.empty or "SpeedST" not in frame:
        return fig
    frame = frame.dropna(subset=["SpeedST"])
    if frame.empty:
        return fig
    for klass in sorted(frame["Class"].dropna().unique()):
        rows = frame[frame["Class"] == klass]
        fig.add_box(
            y=rows["SpeedST"], name=str(klass), marker_color=get_class_color(str(klass))
        )
    fig.update_layout(
        xaxis_title="Class", yaxis_title="Top speed (km/h)", showlegend=False
    )
    return fig
