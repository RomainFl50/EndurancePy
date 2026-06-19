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
- ✅ **Driver changes** are marked on `plot_strategy` (a caret at each new-driver
  stint). Pit-stop *durations* still need the raw `PIT_TIME` (not kept — backlog).

### Colour & style system

- ✅ **`get_car_style()`** — a class colour **plus** a per-car dash/marker, so the
  cars sharing one class colour stay distinguishable.
- ✅ **De-duplicated legend** — charts group traces by class (one legend header per
  class), so the `seen: set` copy-paste is gone.
- ✅ **`get_team_color` + `TEAM_COLORS`** — team colours matched on a distinctive
  substring of the entrant name.
- **Per-series palettes** (IMSA GTP/GTD vs WEC Hypercar/LMGT3) and wider coverage.

### Axes & theming

- ✅ **Lap-time axis & hover formatting** — Plotly charts use a clock axis
  (`M:SS.mmm`) and format hovers via `format_timedelta`; `laptime_formatter()` /
  `format_time_axis(ax)` do the same on the matplotlib/seaborn path. (Timple is
  the matplotlib-only alternative — see the library notes below.)
- ✅ **Track-status overlay** — `add_track_status(fig, source)` shades FCY / safety
  car / code 60 / red-flag lap windows on any lap-axis chart.
- ✅ **Light/dark theme** — `setup_mpl(theme="light"|"dark")`.
- **Seaborn static path** (ready-made static `plot_pace`/distribution charts on
  top of the styling helpers).

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

## Beyond 0.3.0 — future versions

Framed as a fan/analyst: the things that make you actually *understand* an
endurance race. Versions are a direction, not a promise; each item notes when it
depends on data we still need to verify.

### 0.4.0 — Race-craft & strategy analysis

The story of an endurance race *is* strategy — this is where the library earns
its keep for analysts.

- **Pit-stop analysis** — ✅ the raw `PitTime` is now kept on each in-lap;
  `pit_stops()` lists every stop and `plot_pit_stops` charts them. Still to come:
  per-stop pit-lane loss and **undercut / overcut** detection.
- **Stint & degradation** — fuel-corrected pace, a per-stint degradation slope and
  tyre-life estimate, "best achievable" vs actual.
- **Driver analysis** — per-driver pace (median + consistency), time in car, day
  vs night running, best/worst stint; crew comparison across the whole race.
- **Gap / interval engine** — real on-track intervals (not just lap-aligned),
  time lost in traffic, **battle detection** (cars within Xs for N laps), lead
  changes and laps-in-the-lead per car/class.
- **Session context fill** — populate `Hour` / `LapStartDate`, enabling a real
  time axis and day/night shading on the charts. Also the deferred session
  `Duration` / `EndTime` for non-races (from the lap data).

### 0.5.0 — Season & championship

Zoom out from one race to the title fight.

- **Series-specific points** on top of the generic `compute_standings` — WEC /
  IMSA / ELMS systems, Le Mans multipliers, drop scores, pole / fastest-lap
  points.
- **Cross-event trends** — a car / driver / manufacturer's form across a season;
  qualifying vs race pace; grid vs finish.
- **Driver categories** (Bronze / Silver / Gold / Platinum) and **entry metadata**
  (chassis / engine / tyre / category) — *if* the entry list / Classification CSV
  exposes them. Am-class Bronze pace is a story of its own.
- **Manufacturer / BoP lens** — class-performance comparison across events (data
  permitting), to follow the Balance-of-Performance narrative.

### 0.6.0 — Live

Follow it as it happens.

- **Live timing** via the existing `live` extra (socket.io) — streaming laps,
  positions and gaps; live-updating charts; event hooks (pit, lead change, FCY).

### Data & ecosystem (continuous)

- Verified **Classification-CSV parser** — grid, points and penalties straight
  from source (results are reconstructed from the laps today).
- Wider **series / season coverage** & fixtures across WEC / ELMS / Asian Le Mans
  / Le Mans Cup / IMSA, including historical archives (Le Mans deep dives).
- **Race-report generator + CLI** — `endurancepy report 2024 WEC "Le Mans"` → one
  shareable HTML with the strategy, race trace, gaps, pit stops and standings.
- **Exports** (CSV / Parquet) and a hosted **docs site** with a rendered gallery.
- **Plotting** — seaborn static charts, per-series palettes, animated
  position/gap evolution.

## Non-goals

- **Car telemetry / per-driver channels** — no public endurance source exists.
- **A track map** — no public GPS / positional source for these archives.
- **Replicating a championship's exact regulations** — EndurancePy stays a
  generic, configurable toolkit, not a rules engine.
