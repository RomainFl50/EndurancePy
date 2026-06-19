# Plotting

EndurancePy's `plotting` module mirrors `fastf1.plotting`, adapted to endurance:
colours are keyed by **class / manufacturer / team** (not driver), and the
signature charts are **interactive** because a 50-car, 24-hour race is unreadable
as a static image.

Two backends, behind optional extras:

```bash
pip install "endurancepy[interactive]"   # plotly — the interactive charts
pip install "endurancepy[plot]"          # matplotlib — static styling helpers
```

Every chart helper takes a loaded `Session` **or** a `Laps` table and returns the
native figure (a `plotly.graph_objects.Figure`), so you can keep customising it
and then `fig.show()` / `fig.write_html("out.html")`.

```python
import endurancepy as ep
from endurancepy import plotting

ep.Cache.enable_cache("./cache")
session = ep.get_session(2019, "WEC", "Spa", "Race")
session.load(season="08_2018-2019")
```

## Interactive charts (Plotly)

| Function | What it shows |
|---|---|
| `plot_strategy(session)` | Stint/strategy Gantt — one bar per stint per car; gaps are pit stops; driver changes marked. |
| `plot_lap_evolution(session)` | Lap time vs lap, one line per car (clock axis). |
| `plot_pace(session, kind="box"\|"violin")` | Lap-time distribution per class. |
| `plot_stint_pace(session, car=...)` | Lap time vs lap-in-stint — tyre/fuel degradation. |
| `plot_position_evolution(session, in_class=False)` | Position lap-by-lap (P1 on top). |
| `plot_gap(session, in_class=False)` | Gap to the (class) leader over the laps. |
| `plot_race_trace(session)` | Cumulative delta to a constant reference pace. |
| `plot_fastest_laps(session)` | Each car's best lap as a bar (delta to overall best). |
| `plot_driver_comparison(session, car)` | Pace distribution per driver in a crew. |
| `plot_top_speeds(session)` | Top-speed (km/h) distribution per class. |
| `add_track_status(fig, session)` | Shade FCY / safety-car / code-60 / red-flag lap windows on any lap-axis chart. |

```python
plotting.plot_strategy(session).show()

# Race trace with the neutralisations shaded in
fig = plotting.plot_race_trace(session)
plotting.add_track_status(fig, session)
fig.write_html("race_trace.html")
```

## Colours & styles

| Function | Returns |
|---|---|
| `get_class_color(name)` | Hex colour for a racing class (Hypercar / LMP2 / LMGT3 / GTP / GTD…). |
| `get_manufacturer_color(name)` | Hex colour for a manufacturer. |
| `get_team_color(name)` | Hex colour for a team (matched on a distinctive substring of the entrant). |
| `get_car_style(car, class)` | `{"color", "dash", "symbol"}` — class colour + a per-car dash/marker so cars sharing a class colour stay distinguishable. |

The registries `CLASS_COLORS` / `MANUFACTURER_COLORS` / `TEAM_COLORS` (and
`list_classes()` / `list_manufacturers()` / `list_teams()`) are public; unknown
names fall back to `DEFAULT_COLOR`.

## Static path (matplotlib / seaborn)

For publication / PDF figures and statistical plots:

```python
plotting.setup_mpl(theme="dark")   # or "light"; sensible rcParams

import seaborn as sns
ax = sns.boxplot(...)              # y = LapTime.dt.total_seconds()
plotting.format_time_axis(ax, "y")  # ticks read M:SS.mmm instead of seconds
```

`laptime_formatter()` returns the underlying `matplotlib` tick formatter if you
want to apply it yourself. (FastF1 uses the external *Timple* package for the same
job; it is matplotlib-only and unrelated to the Plotly path.)

## Examples

Runnable scripts in [`examples/`](../examples): `plot_strategy.py` and
`plot_race_trace.py` write standalone interactive HTML; the
[`quickstart.ipynb`](../examples/quickstart.ipynb) notebook has an interactive
plotting section. See also the [ROADMAP](../ROADMAP.md) for what's next.
