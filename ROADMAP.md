# EndurancePy roadmap

Where the project is heading. This is a direction, not a contract — items move,
merge or drop as we learn. For what has shipped, see [`CHANGELOG.md`](CHANGELOG.md).

Guiding principles:

- **FastF1-shaped, endurance-native.** Mirror FastF1's ergonomics where they fit,
  but model the *car/crew/class* (not the driver) — endurance has no per-driver
  telemetry and no per-driver colours.
- **pandas-first.** Data objects are `DataFrame`/`Series` subclasses; helpers
  return them (or `(fig, ax)`), so users can always compose.
- **Honest about the source.** We only expose what the Al Kamel archives actually
  contain; what we can't get cheaply is documented, not faked. (No car telemetry
  exists publicly for endurance — that is a permanent non-goal.)
- **Optional heavy deps.** Plotting/interactive backends live behind extras
  (`pip install endurancepy[plot]`); the core stays light.

---

## 0.3.0 — Plotting (the focus)

Today `endurancepy.plotting` ships only colour helpers (`get_class_color`,
`get_manufacturer_color`) + `setup_mpl`, and every chart in `examples/` is
hand-built. 0.3.0 turns plotting into a first-class, endurance-aware feature.

### Signature chart helpers

Reusable functions that return the native figure (a `plotly.Figure` on the
interactive path, or matplotlib `(fig, ax)` on the static path) — composable,
never showing/blocking internally. (✅ = shipped.)

- ✅ **`plot_strategy(session)`** — Gantt of the stints: one horizontal bar per
  car, segmented by stint, the gaps being pit stops. *The* endurance plot.
- ✅ **`plot_race_trace(session)`** — cumulative delta of each car vs a reference
  pace ("race trace"): exposes position battles and the cost of neutralisations.
- ✅ **`plot_position_evolution(session)`** — position lap-by-lap, overall and per
  class (`in_class=`).
- ✅ **`plot_gap(session)`** — gap to the (class) leader over the laps.
- ✅ **`plot_pace(session)`** (box/violin) / ✅ **`plot_lap_evolution(session)`** —
  pace distribution per class and the per-car evolution lines.
- ✅ **`plot_driver_comparison(car)`** — pace distribution per driver within a crew.
- ✅ **`plot_fastest_laps`** — best lap per car (delta to overall best), by class.
- ✅ **`plot_stint_pace`** — lap time vs lap-in-stint (tyre/fuel degradation).
- ✅ **`plot_top_speeds`** — top-speed distribution per class.
- Mark pit stops / driver changes explicitly on `plot_strategy` (pit-stop
  *durations* need the raw `PIT_TIME`, not currently kept — see backlog).

### Colour & style system

- ✅ **`get_car_style()`** — a class colour **plus** a per-car dash/marker, so the
  cars sharing one class colour stay distinguishable.
- ✅ **De-duplicated legend** — charts group traces by class (one legend header per
  class), so the `seen: set` copy-paste is gone.
- **`get_team_color` + a team registry** (today only class + manufacturer; FastF1
  has team colours).
- **Per-series palettes** (IMSA GTP/GTD vs WEC Hypercar/LMGT3) and wider coverage.

### Axes & theming

- ✅ **Lap-time axis & hover formatting** — lap-time charts use a clock axis
  (`M:SS.mmm`) and hovers render durations via `format_timedelta`. (A
  `matplotlib.ticker` Formatter for the seaborn path is still to do; Timple is the
  matplotlib-only alternative — see the library notes below.)
- ✅ **Track-status overlay** — `add_track_status(fig, source)` shades FCY / safety
  car / code 60 / red-flag lap windows on any lap-axis chart.
- **Light/dark theme** and a richer `setup_mpl(theme=...)` (fonts, rcParams).
- **Seaborn static path** (`plot_pace` as violin/box, publication styling).

### Data prerequisites (done *with* the plotting)

- ✅ **Per-lap `GapToLeader` / `GapToLeaderInClass`** computed in the Analysis
  parser (`Position` / `PositionInClass` were already derived). These underpin the
  gap, position and trace charts.
- **`Hour`** (and the session `Duration`/end time we deferred) for time axes.

---

## Plotting library evaluation

0.3.0 needs a backend decision. Endurance fields are **large** (often 30–60+ cars)
and races are **long** (6–24 h, hundreds of laps), so a static chart of the whole
field turns into spaghetti fast. **Interactivity is therefore a requirement, not a
nicety**: zoom into a stint window, hover for car/driver/lap/gap, and click the
legend to isolate a car or class. Plain matplotlib output also just looks dated
next to Plotly/seaborn.

| Library | Strengths | Trade-offs | Fit for EndurancePy |
|---|---|---|---|
| **Plotly** | Interactive by default (zoom/pan/hover, legend-toggle to isolate a car/class), notebook-native, standalone-HTML export, modern look | Heavier dep; large JSON for very long races (mitigated by `Scattergl`/WebGL) | **Primary/default backend** — the dense timelines (strategy, trace, gap, evolution) need it |
| **Seaborn** | Polished statistical charts (violin/box/KDE of pace) over matplotlib; great for print/PDF | Static; thin wrapper, so bespoke timelines still need raw matplotlib | **Static "pretty" path** — pace distributions & publication figures |
| **Matplotlib** | Total low-level control; what FastF1 uses; engine under seaborn | No interactivity; dated default style; weak timedelta axes (needs Timple) | The engine under seaborn / static fallback — not the user-facing default |
| **Bokeh** | Interactive, streaming/server, scales to large data | More verbose than Plotly; server model is overkill here | Later, only if a live/dashboard angle appears |
| **HoloViews + Datashader** | Renders millions of points, pixel-accurate, zoomable | Conceptual weight; another abstraction | Escalation only, if Plotly+WebGL hits a perf wall (full field × 24 h) |
| **Altair (Vega-Lite)** | Declarative grammar-of-graphics, faceting | Awkward for custom timelines (Gantt/trace); data-size limits | Not planned |
| **Timple** | matplotlib timedelta locators/formatters (by FastF1's author) | **matplotlib-only**; dormant (last release 0.1.6, May 2023) | Only on the seaborn/matplotlib path; otherwise superseded by our own formatter |

**Recommendation:** Plotly-first (interactive), seaborn for static stats.

1. **Plotly is the default backend** for the dense, signature charts (strategy
   Gantt, race trace, position/gap evolution, lap evolution). Interactivity —
   zoom into a stint, hover for car/driver/lap/gap, legend-toggle a class — is
   what keeps a 50-car / 24 h chart readable. Use `Scattergl` (WebGL) for the
   high-point-count traces, and export standalone HTML for sharing.
2. **Seaborn for the static, statistical "pretty" path** (pace distributions:
   violin/box/KDE per class) and clean print/PDF figures.
3. **Duration formatting** is done with our own `format_timedelta` — as Plotly
   tick text / `hovertemplate` on the Plotly path, and a small matplotlib
   `Formatter` on the seaborn path. **Timple** is matplotlib-only and dormant, so
   it's a documented opt-in for the seaborn path, not a dependency.
4. Helpers stay **backend-aware but return the native figure** (`plotly.Figure`
   or matplotlib `(fig, ax)`) so users can keep customising.
5. Defer **Bokeh** and **HoloViews/Datashader** unless a dashboard need or a real
   Plotly performance wall shows up.

---

## Backlog (beyond 0.3.0)

Not scheduled, roughly by value:

- **Session end time / accurate durations.** `get_sessions()` exposes a `Duration`
  only for races (from the per-hour folders). True durations for practice/
  qualifying need the lap data (last lap's `Time`); candidate for an opt-in
  `get_sessions(exact=True)` or an `EndTime` column.
- **Pit-stop analysis** (count, stationary time, pit loss). The raw `PIT_TIME` is
  currently dropped and the stationary time is folded into the out-lap, so a
  reliable pit-stop chart needs `PIT_TIME` kept on the laps first.
- **Classification-CSV parser.** Results are currently reconstructed from the laps;
  parse the real Classification CSV once its layout is fully verified (grid,
  points, status straight from source).
- **Wider series/season coverage & fixtures** — more verified formats across WEC /
  ELMS / Asian Le Mans / Le Mans Cup / IMSA, including older archives.
- **Standings** — richer, series-specific points/regulations on top of the generic
  `compute_standings` (bonus/pole points, drop scores, Le Mans multipliers).
- **Docs** — a "plotting gallery" mirroring FastF1's examples gallery, plus a
  fuller user guide.

## Non-goals

- **Car telemetry / per-driver channels** — no public endurance source exists.
- **Replicating any championship's exact regulations** — EndurancePy stays a
  generic, configurable toolkit, not a rules engine.
