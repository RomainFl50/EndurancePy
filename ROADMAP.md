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
never showing/blocking internally:

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

- **Lap-time axis & hover formatting** — durations rendered via the existing
  `format_timedelta`: as Plotly tick text + `hovertemplate` on the interactive
  path, and a small `matplotlib.ticker` Formatter on the seaborn path, so times
  read `1:58.0`, not seconds. (Timple is the matplotlib-only alternative; see the
  library notes below.)
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
