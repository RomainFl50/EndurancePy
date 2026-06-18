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

Reusable functions that return `(fig, ax)` (composable, never `plt.show()`
internally):

- **`plot_strategy(session)`** — Gantt of the stints: one horizontal bar per car,
  segmented by stint, marking pit stops and driver changes. *The* endurance plot.
  (`Stint`, `PitInTime`/`PitOutTime`, `DriverChange` already exist.)
- **`plot_race_trace(session)`** — cumulative delta of each car vs a reference
  pace ("race trace"): exposes position battles and the cost of neutralisations.
- **`plot_position_evolution(session)`** — position lap-by-lap, overall and per
  class.
- **`plot_gap(session)`** — gap to the (class) leader over time.
- **`plot_pace(session)`** / **`plot_lap_evolution(session)`** — box/violin pace
  per class and the evolution scatter (promote the two example charts to the API).
- **`plot_driver_comparison(car)`** — pace distribution per driver within a crew.

### Colour & style system

- **`get_team_color` + a team registry** (today only class + manufacturer; FastF1
  has team colours).
- **`get_car_style()`** — a class/manufacturer colour **plus** a linestyle/marker,
  so the several cars sharing one class colour stay distinguishable (and readable
  in black & white). Needed the moment a whole class is plotted.
- **De-duplicated legend** helper (the `seen: set` pattern is copy-pasted in every
  example today).
- **Per-series palettes** (IMSA GTP/GTD vs WEC Hypercar/LMGT3) and wider coverage.

### Axes & theming

- **Lap-time axis formatter** — a `matplotlib.ticker` Formatter/Locator built on
  the existing `format_timedelta`, so axes read `1:58.0`, not seconds. (FastF1
  leans on the external *Timple* lib for this; see the library notes below.)
- **Track-status overlay** — shade FCY / SC / red-flag windows on any time-axis
  plot. High value given how long endurance races are.
- **Light/dark theme** and a richer `setup_mpl(theme=...)` (fonts, rcParams).

### Data prerequisites (done *with* the plotting)

Some charts need columns that are in the schema but not yet populated:

- **Per-lap `Position` / `PositionInClass` and `GapToLeader(InClass)`** — required
  for the trace / gap / position charts (currently "filled later").
- **`Hour`** (and the session `Duration`/end time we deferred) for time axes.

---

## Plotting library evaluation

0.3.0 needs a backend decision. Endurance races are *long* (6–24 h), so
interactivity (zoom into a stint, hover for car/driver/lap) is unusually valuable
— but bespoke charts (strategy Gantt, race trace) need low-level control.

| Library | Strengths | Trade-offs | Fit for EndurancePy |
|---|---|---|---|
| **Matplotlib** | Static, publication-quality, total control; what FastF1 uses; already our optional `plot` extra | No interactivity; weak native timedelta axes | **Default/static backend** — best for the bespoke Gantt & race-trace |
| **Plotly** | Interactive by default in 2026 (zoom/pan/hover), notebook-native, standalone-HTML export | Heavier dep; large JSON for very long races | **Optional interactive backend** — strong for 24 h zoom/share |
| **Bokeh** | Interactive, streaming/server, scales to large data | More verbose; server model is overkill here | Later, if a live/dashboard angle appears |
| **HoloViews + Datashader** | Renders millions of points, pixel-accurate, zoomable; backend-agnostic | Conceptual weight; another abstraction | Only if perf becomes a real issue (full field × 24 h) |
| **Altair (Vega-Lite)** | Declarative grammar-of-graphics, faceting | Awkward for custom timelines (Gantt/trace); data-size limits | Possible for exploratory/faceted distributions |
| **Seaborn** | Quick statistical charts (violin/box of pace) over matplotlib | Just a matplotlib wrapper; not for bespoke timelines | Convenience only — no hard dependency |
| **Timple** | matplotlib timedelta locators/formatters (by FastF1's author) | Niche, small maintenance surface | Alternative to our own lap-time formatter |

**Recommendation:** matplotlib-first, Plotly-optional.

1. Keep **matplotlib** as the default backend (FastF1 parity, full control for the
   signature charts, already an extra).
2. Add an **optional Plotly backend** (`endurancepy[plot-interactive]`) for the
   charts that benefit most from zoom/hover on a long race; helpers stay
   backend-agnostic by returning a figure object.
3. For lap-time axes, ship a **small in-house formatter** on top of
   `format_timedelta` (no new dependency); document **Timple** as the drop-in
   alternative for users who want its richer locators.
4. Defer **Bokeh** and **HoloViews/Datashader** unless a dashboard need or a real
   performance wall shows up.

---

## Backlog (beyond 0.3.0)

Not scheduled, roughly by value:

- **Session end time / accurate durations.** `get_sessions()` exposes a `Duration`
  only for races (from the per-hour folders). True durations for practice/
  qualifying need the lap data (last lap's `Time`); candidate for an opt-in
  `get_sessions(exact=True)` or an `EndTime` column.
- **Gaps & per-lap positions** computed in the loader (also a plotting prereq, see
  above) — useful on their own for analysis, not just charts.
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
