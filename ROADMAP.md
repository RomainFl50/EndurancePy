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

## Where we are

**0.4.0 is published.** The library loads a session from the Al Kamel archives
(discovery, cache, Analysis/Classification/Weather parsers), exposes
FastF1-style data objects with the `pick_*` filters, ships a full set of
interactive Plotly charts (strategy Gantt, race trace, gaps, positions, pace,
pit stops, with track-status and day/night overlays), and a first layer of
race-craft tables (`pit_stops`, `stint_summary`, `driver_summary`,
`lead_changes`, `battles`, `time_lost`, `fuel_corrected`). Details in the
[CHANGELOG](CHANGELOG.md).

What follows is the plan to 1.0.0: five themed milestones, then the stable
release. Each milestone follows the established release methodology
(CHANGELOG section + version bump in the release PR, manual test plan
`docs/test_plan_<version>.md` run against a real race, tag from `main`,
publishing via the `v*` tag — see `RELEASING.md`).

---

## 0.5.0 — Season & championship

Zoom out from one race to the title fight. This is the last big *data* gap:
everything below one race is covered; nothing above it is.

### Data prerequisites

- **Verified Classification-CSV parser everywhere.** Today race results can be
  read from the Classification CSV, but grid position, points and penalties are
  still reconstructed or missing. Verify the real columns across series/years
  (same probe approach as 0.1.0) and expose **grid, points, penalties, status
  (running / retired / NC / DSQ)** straight from source.
- **Entry metadata** — chassis / engine / tyre supplier and **driver categories**
  (Bronze / Silver / Gold / Platinum), *if* the entry list or Classification CSV
  exposes them. Am-class Bronze pace is a story of its own.

### Features

- **Series-specific points** on top of the generic `compute_standings` — named
  presets for the WEC / IMSA / ELMS systems, Le Mans multipliers, drop scores,
  pole / fastest-lap bonus points. Presets stay *configurations* of the generic
  calculator, not a rules engine (see non-goals).
- **Season loader** — `get_season(year, series)`-style convenience that loads
  every race of a season (cached), so cross-event work is one call, not a loop.
- **Cross-event trends** — a car / driver / manufacturer's form across a season:
  qualifying vs race pace, grid vs finish, pace rank round by round.
- **Manufacturer / BoP lens** — class-performance comparison across events
  (data permitting), to follow the Balance-of-Performance narrative.
- **Championship charts** — `plot_standings_evolution` (points round by round,
  per class) and a season-form heatmap (car × round).

Exit criteria: reproduce a full WEC and ELMS season's final standings (all
classes) from source data, and tell the story of a title fight in one notebook
(`docs/test_plan_0.5.0.md`).

## 0.6.0 — Race-craft, deeper

Finish what 0.4.0 started: everything marked "still to come" in the strategy
layer, now that the simple versions have proven the shape of the API.

- **Real on-track intervals** — gaps interpolated at the crossing times (not
  just lap-aligned), so `battles()` and `plot_gap` reflect what you'd see at the
  track. This is the interval engine v2 that several 0.4.0 tables were waiting
  for.
- **Pit economics** — pit-lane *time loss* (vs drive-through time, per track,
  estimated from the data) and proper **pairwise undercut/overcut attribution**
  (who gained on whom across a stop window), replacing the rough
  `PlacesGained` proxy.
- **Tyre-life estimates** — extend `stint_summary`'s degradation slope into a
  usable tyre model: predicted cliff, optimal stint length per class/car.
- **Driver analysis, completed** — day vs night running splits, best/worst
  stint per driver, traffic-adjusted pace (building on `time_lost`).
- **Session context, completed** — `LapStartDate` (needs the session date,
  available via `Event.get_dates()`), and the deferred session `Duration` /
  `EndTime` for non-race sessions.
- **Chart upgrades** — pit-stop durations rendered on `plot_strategy` (the
  `PitTime` is kept since 0.4.0), and undercut/overcut annotations on the
  race trace.

Exit criteria: a Le Mans 24h strategy deep-dive notebook whose numbers
(intervals, pit loss, tyre life) survive a sanity check against the broadcast
narrative (`docs/test_plan_0.6.0.md`).

## 0.7.0 — Reporting, exports & the docs site

Make the library's output *shareable* — the milestone where EndurancePy stops
being notebook-only.

- **Race-report generator + CLI** — `endurancepy report 2024 WEC "Le Mans"` →
  one standalone shareable HTML: strategy Gantt, race trace, gap chart, pit
  stops, results and (0.5.0 permitting) championship impact. The CLI is a thin
  layer over a `report(session)` API.
- **Exports** — first-class CSV / Parquet export of every data object
  (`Laps`, `SessionResults`, the strategy tables), round-trippable.
- **Hosted docs site** — API reference + narrative guides + the plotting
  gallery, with executed notebooks (rendered offline in CI via the faked
  download layer, like `examples/` today). Publish on tagged releases.
- **Static plotting path** — the seaborn/matplotlib "pretty" variants of the
  distribution charts (`plot_pace`, driver comparison) for print/PDF, on top of
  `setup_mpl` + `format_time_axis`.
- **Per-series palettes** — IMSA (GTP/GTD…) vs WEC/ELMS (Hypercar/LMGT3…)
  colour sets and wider team/manufacturer coverage.
- **Animated evolution charts** — animated position/gap evolution (Plotly
  frames) for social-media-friendly output.

Exit criteria: `pip install endurancepy && endurancepy report …` produces a
report a race fan would actually share; docs site live
(`docs/test_plan_0.7.0.md`).

## 0.8.0 — Live

Follow it as it happens. Deliberately *after* the reporting milestone: live
reuses the charts and tables, streaming into them.

- **Live timing client** via the existing `live` extra (socket.io) — streaming
  laps, positions and gaps into the same `Laps`/`SessionResults` shapes, so
  every existing table and chart works on a live session.
- **Live-updating charts** — the Plotly figures refresh as laps arrive
  (notebook first; a dashboard server stays out of scope unless demand shows).
- **Event hooks** — callbacks on pit entry, lead change, FCY/safety car, so
  users can script alerts.
- **Replay mode** — feed a recorded stream back through the live path, for
  offline development and tests (no live dependency in CI, same philosophy as
  the faked download layer).

Exit criteria: follow a real race weekend live end-to-end; the replay fixture
of that stream becomes the regression test (`docs/test_plan_0.8.0.md`).

## 0.9.0 — Coverage, hardening & API freeze

The release-candidate milestone: no new feature themes, everything aimed at
making 1.0.0 boring.

- **Coverage sweep** — verify loading + parsing across all supported series
  (WEC / ELMS / Asian Le Mans / Le Mans Cup / IMSA) and back through the
  historical archives (Le Mans deep dives); grow the synthetic fixture set to
  cover every format quirk found.
- **Performance pass** — full-field 24 h sessions (60+ cars, thousands of laps):
  parse time, memory, chart responsiveness (`Scattergl` where needed), cache
  behaviour.
- **API review & freeze** — one pass over the whole public surface for naming
  and signature consistency (FastF1 parity where it applies); execute all
  pending deprecations; from here to 1.0.0, breaking changes only with a
  deprecation cycle.
- **Robustness** — every loader/table degrades gracefully on partial data
  (typed-but-empty, documented); error messages say *which* file/column was the
  problem.
- **Docs completeness** — every public name documented on the site; the
  gallery covers every chart; `py.typed` shipped and mypy-clean strictness
  raised where cheap.

Exit criteria: the 1.0.0 checklist below is green except the soak time.

## 1.0.0 — Stable

A promise, not a feature drop. 1.0.0 is 0.9.x plus soak time and the semver
contract:

- **Semver applies to the documented public API** — the top-level `endurancepy`
  namespace, the data objects and their documented columns, the `pick_*`
  filters, the strategy tables, `plotting`, and the CLI. Internals
  (`alkamel.*` parsing details, cache layout) stay changeable; the cache is
  versioned by `PARSER_VERSION` anyway.
- **Release checklist** — all series in the coverage sweep load; docs site
  complete; zero known data-corruption bugs; deprecation policy documented;
  0.9.x has soaked through at least one real race weekend without a hotfix.
- Then: cut, tag, publish — same procedure as every release, just with a
  bigger number.

After 1.0.0, the same themes continue as 1.x minors (new seasons/series as
they publish, more presets, chart requests) under the semver contract.

---

## Continuous (any milestone)

Not tied to a version — picked up whenever they're cheap or needed:

- New seasons/series fixtures as Al Kamel publishes them; format-drift watch
  (the `network`-marked integration test is the canary).
- Palette & team-colour upkeep (entry lists change every season).
- Community health: triage, issue templates, contribution docs staying true.

## Non-goals

- **Car telemetry / per-driver channels** — no public endurance source exists.
- **A track map** — no public GPS / positional source for these archives.
- **Replicating a championship's exact regulations** — EndurancePy stays a
  generic, configurable toolkit (with per-series *presets*), not a rules
  engine.
- **A hosted dashboard/service** — the library renders standalone HTML and
  notebooks; running servers for people is out of scope.

---

## Appendix — plotting backend evaluation (decided, shipped in 0.3.0)

Kept for the record: why Plotly-first. Endurance fields are **large** (often
30–60+ cars) and races are **long** (6–24 h, hundreds of laps), so a static
chart of the whole field turns into spaghetti fast. **Interactivity is
therefore a requirement, not a nicety**: zoom into a stint window, hover for
car/driver/lap/gap, and click the legend to isolate a car or class.

| Library | Strengths | Trade-offs | Fit for EndurancePy |
|---|---|---|---|
| **Plotly** | Interactive by default (zoom/pan/hover, legend-toggle to isolate a car/class), notebook-native, standalone-HTML export, modern look | Heavier dep; large JSON for very long races (mitigated by `Scattergl`/WebGL) | **Primary/default backend** — the dense timelines (strategy, trace, gap, evolution) need it |
| **Seaborn** | Polished statistical charts (violin/box/KDE of pace) over matplotlib; great for print/PDF | Static; thin wrapper, so bespoke timelines still need raw matplotlib | **Static "pretty" path** — pace distributions & publication figures (0.7.0) |
| **Matplotlib** | Total low-level control; what FastF1 uses; engine under seaborn | No interactivity; dated default style; weak timedelta axes (needs Timple) | The engine under seaborn / static fallback — not the user-facing default |
| **Bokeh** | Interactive, streaming/server, scales to large data | More verbose than Plotly; server model is overkill here | Later, only if a live/dashboard angle appears |
| **HoloViews + Datashader** | Renders millions of points, pixel-accurate, zoomable | Conceptual weight; another abstraction | Escalation only, if Plotly+WebGL hits a perf wall (full field × 24 h) |
| **Altair (Vega-Lite)** | Declarative grammar-of-graphics, faceting | Awkward for custom timelines (Gantt/trace); data-size limits | Not planned |
| **Timple** | matplotlib timedelta locators/formatters (by FastF1's author) | **matplotlib-only**; dormant (last release 0.1.6, May 2023) | Only on the seaborn/matplotlib path; otherwise superseded by our own formatter |

The outcome: Plotly is the default backend (shipped 0.3.0, `interactive`
extra); duration formatting via our own `format_timedelta`; helpers return the
native figure; seaborn arrives with the static path in 0.7.0; Bokeh /
HoloViews stay deferred unless a real performance wall shows up.
