# Implementation plan — 0.5.0 "Season & championship"

> Technical framing document for the 0.5.0 milestone (see `ROADMAP.md`,
> "0.5.0 — Season & championship"). It follows the precedent of
> [`plan_implementation.md`](plan_implementation.md): plan first, code after.
> Everything here extends the current public API (0.4.0) — nothing below
> contradicts a shipped signature.

---

## 1. Goals & non-goals

**Goal.** Zoom out from one race to the title fight: verified championship
data (grid, points, penalties, status) straight from the Classification CSV,
a one-call season loader, series points *presets* on top of the generic
`compute_standings`, cross-event trend tables, and two championship charts.

**Non-goals** (per the roadmap's standing non-goals):

- **No rules engine.** Presets are plain *configurations* (a points table +
  a few knobs) of the generic calculator. We do not model eligibility,
  appeals, part-season invitational entries, or every regulation revision.
  Preset values carry a year tag (`"wec_2024"`) and a docstring pointing at
  the sporting regulations they were transcribed from; when a season's rules
  are out of reach, the user passes their own numbers.
- **No official-standings scraping.** Standings are always *recomputed* from
  session results (or summed from source `Points` where the CSV provides
  them); the official tables are only used offline to validate.
- **Per-driver championships** (crews change per round) are best-effort in
  0.5.0: `by="Crew"` works on the crew string; a real per-driver explode is
  deferred unless it falls out cheaply (see §7).

## 2. Data verification (prerequisite, blocks the parser work)

The dev sandbox cannot reach the Al Kamel portals, so — same approach as
0.1.0 ("verified real Al Kamel formats, captured via a one-off GitHub
Actions probe") — format verification runs on a networked GitHub Actions
runner:

1. A one-off, manually-triggered workflow (a temporary sibling of
   `.github/workflows/integration.yml`) downloads Classification CSVs (and
   any entry-list-like files found in the session file index) across a
   matrix: WEC 2018-19 / 2023 / 2024, ELMS 2023 / 2024, IMSA 2023 / 2024,
   race + qualifying + practice.
2. The job prints **headers plus 2–3 sample rows** per file into the log /
   an ephemeral artifact. Nothing is committed — findings are transcribed
   into this plan, the parser, and *synthetic* fixtures (repo rule: no raw
   Al Kamel data in the repo).
3. Specific questions the probe must answer:
   - Do any Classification variants carry **POINTS / GRID / PENALTY**
     columns, and under what names? The verified 0.1.0 race header
     (`POSITION;NUMBER;TEAM;DRIVER_1..5;VEHICLE;TYRES;CLASS;GROUP;DIVISION;
     STATUS;LAPS;TOTAL_TIME;GAP_FIRST;GAP_PREVIOUS;FL_LAPNUM;FL_TIME;FL_KPH`)
     has **none of them** — see risk R1.
   - The full vocabulary of `STATUS` (Classified / Running / Retired /
     Not classified / Disqualified / Excluded …) per series.
   - Entry metadata: is there an entry-list CSV (chassis / engine / tyre
     supplier / driver Bronze–Silver–Gold–Platinum categories), or are
     `VEHICLE` / `TYRES` in the Classification all we get?
   - Whether a *grid* CSV (or the qualifying Classification) is the
     canonical grid source when the race CSV lacks a GRID column.

## 3. API design

### 3.1 `SessionResults` — columns exposed from source

`_types.RESULTS_COLUMNS` already reserves `GridPosition` (`Int64`) and
`Points` (`float64`); `alkamel/classification.py` starts filling them from
whatever the probe confirms. New columns (all typed-but-empty when absent):

| Column | dtype | Source |
|---|---|---|
| `Vehicle` | `string` | `VEHICLE` (full chassis name; `Manufacturer` stays the derived first word) |
| `Tyres` | `string` | `TYRES` (already in the verified header) |
| `Penalties` | `string` | penalty column(s), verbatim until formats are known |
| `DriverCategories` | `string` | Bronze/Silver/… per driver, `"; "`-joined aligned with `Crew` (entry list permitting) |

`Status` normalisation: raw text is kept in `Status`; `ClassifiedPosition`
adopts the FastF1 letter convention for non-finishers (`"R"` retired, `"D"`
disqualified, `"N"` not classified) instead of always stringifying the
position. `results.from_laps` keeps producing these columns as empty — the
laps cannot know grid or points.

### 3.2 Points presets — `standings.py`

A preset is a frozen dataclass bundling the knobs of one championship/year;
`compute_standings` grows the corresponding generic parameters, all
defaulting to "off" (fully backwards compatible):

```python
@dataclass(frozen=True)
class PointsScheme:
    points: Sequence[float]                 # P1 first (existing convention)
    pole_bonus: float = 0.0                 # GridPosition == 1 (per class if per_class)
    fastest_lap_bonus: float = 0.0          # min BestLapTime (per class if per_class)
    drop: int = 0                           # n worst round scores dropped per entrant
    round_multipliers: dict[str, float] = field(default_factory=dict)
    # e.g. {"Le Mans": 2.0}: substring-matched against the round's EventName

POINTS_PRESETS: dict[str, PointsScheme]     # "wec_2024", "elms_2024", "imsa_2024", ...

def compute_standings(
    results: Iterable[pd.DataFrame],
    *,
    points: str | Sequence[float] | dict[int, float] | PointsScheme | None = None,
    by: str = "CarNumber",
    per_class: bool = False,
    round_names: Sequence[str] | None = None,   # aligns multipliers with rounds
    use_source_points: bool = False,            # sum the CSV Points column instead
) -> Standings: ...
```

- `points` now also accepts a `PointsScheme` or a preset name; plain
  strings keep resolving through `POINTS_SYSTEMS` first (unchanged).
- Bonuses are computed from the results rows themselves (`GridPosition`,
  `BestLapTime`) — no extra inputs, which is why WP2 precedes full-fidelity
  presets.
- `Standings` gains per-round point columns (`R1`, `R2`, … or the round
  names) so the evolution chart and drop-score audit need no re-run, plus a
  `Dropped` column when `drop > 0`.
- `use_source_points=True` is the "straight from source" path (data
  permitting); computed-vs-source is the validation of the presets.

### 3.3 Season loader — `season.py` (new module)

```python
class Season:                                # plain class, not a DataFrame
    year: int
    series: Series
    schedule: EventSchedule                  # existing object
    def load(self, *, sessions=("Race",)) -> None: ...   # sequential, cache-backed
    def races(self) -> dict[int, Session]: ...           # round -> loaded Session
    def results(self, session: str = "Race") -> pd.DataFrame: ...
        # concatenated SessionResults with RoundNumber / EventName prepended
    def standings(self, *, points=None, by="CarNumber", per_class=False) -> Standings:
        # forwards to compute_standings with round_names filled from the schedule

def get_season(year: int, series: str | Series, *, season: str | None = None) -> Season: ...
```

Built entirely on the existing layers: `get_event_schedule` for the
calendar, `Event.get_session(...).load()` per round, the two-stage `Cache`
for idempotence — **no new cache layer**; a re-run is all cache hits.
Rounds that fail to load are skipped with a logged warning (typed-but-empty
philosophy), so a mid-season call works.

### 3.4 Cross-event trends — `trends.py` (new module)

Same conventions as `strategy.py`: each accepts a `Season`, a list of
`Session`s/results, or a plain concatenated DataFrame; returns a
typed-but-empty DataFrame when there is nothing to say.

| Function | One row per | Columns |
|---|---|---|
| `grid_vs_finish(source, *, in_class=True)` | car × round | `CarNumber, Class, RoundNumber, EventName, GridPosition, Position[InClass], PlacesGained` |
| `pace_ranks(source, *, by="CarNumber")` | car × round | `…, MedianClean` (Timedelta, from clean-lap median), `PaceRank` (within class), `GapToClassBest` (Timedelta) |
| `quali_race_delta(source)` | car × round | `…, QualiBest, RaceMedian, QualiGap, RaceGap` (each gap vs class best, Timedelta) — needs `sessions=("Qualifying", "Race")` loaded |
| `manufacturer_pace(source)` | manufacturer × class × round | `Manufacturer, Class, RoundNumber, EventName, BestLap, MedianClean, GapToClassBest, Cars` — the BoP lens |

Lap-based tables reuse `strategy._clean_laps` (green-flag, accurate,
non-box laps); durations stay `pandas.Timedelta` end to end.

### 3.5 Championship charts — `plotting/charts.py`

```python
def plot_standings_evolution(source, *, points=None, by="CarNumber",
                             class_: str | None = None,
                             title="Championship evolution") -> go.Figure: ...
    # cumulative points after each round, one line per entrant; hover shows
    # the round score; Le Mans-style multiplied rounds annotated.
def plot_season_heatmap(source, *, metric="PositionInClass",
                        class_: str | None = None,
                        title="Season form") -> go.Figure: ...
    # car x round heatmap; metric in {"PositionInClass", "Position", "PaceRank", "Points"}
```

Both follow the existing chart conventions (return a native Plotly figure,
class colours via `plotting.colors`, guarded by the `interactive` extra).

## 4. Module-by-module change list

| File | Change |
|---|---|
| `src/endurancepy/_types.py` | add `Vehicle`, `Tyres`, `Penalties`, `DriverCategories` to `RESULTS_COLUMNS` |
| `src/endurancepy/alkamel/classification.py` | fill `GridPosition`/`Points`/`Penalties`/new metadata per verified headers; `Status` → FastF1-style `ClassifiedPosition` letters |
| `src/endurancepy/alkamel/entrylist.py` (new, only if the probe finds a source) | entry-list CSV → per-car metadata merged into results |
| `src/endurancepy/results.py` | keep the new columns typed-but-empty in `from_laps` |
| `src/endurancepy/standings.py` | `PointsScheme`, `POINTS_PRESETS`, extended `compute_standings` (§3.2), per-round columns on `Standings` |
| `src/endurancepy/season.py` (new) | `Season`, `get_season` (§3.3) |
| `src/endurancepy/trends.py` (new) | the four trend tables (§3.4) |
| `src/endurancepy/plotting/charts.py` | `plot_standings_evolution`, `plot_season_heatmap` |
| `src/endurancepy/__init__.py` | export `get_season`, `Season`, `PointsScheme`, `POINTS_PRESETS`, the trend tables |
| `src/endurancepy/cache.py` | bump `PARSER_VERSION` **only if** a cached table's schema changes (laps are unaffected; results are re-parsed, so likely no bump) |
| `tests/`, `examples/`, `docs/` | see §6 and §8; `CHANGELOG.md` + `ROADMAP.md` per PR, as always |

## 5. Work breakdown (PR-sized packages)

| WP | Content | Depends on | Parallel? |
|---|---|---|---|
| **WP1** | Probe workflow + format findings written into this doc (§2) | — | first |
| **WP2** | Classification parser upgrade + `RESULTS_COLUMNS` + status normalisation + synthetic fixtures for each verified variant | WP1 | — |
| **WP3** | `PointsScheme` / presets / `compute_standings` extensions; generic machinery (drop, multipliers, per-round columns) is WP1-independent — bonus wiring lands once WP2's columns exist | WP1 (values), WP2 (bonuses) | ∥ WP2 (machinery part) |
| **WP4** | `Season` + `get_season` | — (builds on shipped events/discovery/cache) | ∥ WP1–3 |
| **WP5** | `trends.py`: `grid_vs_finish`, `pace_ranks`, `quali_race_delta`, `manufacturer_pace` | WP2 (grid), WP4 | ∥ WP3 |
| **WP6** | Charts: `plot_standings_evolution`, `plot_season_heatmap` | WP3, WP4 (heatmap also WP5 for `PaceRank`) | ∥ WP5 |
| **WP7** | Validation & release: reproduce WEC + ELMS final standings on a networked runner, title-fight notebook in `examples/`, `docs/test_plan_0.5.0.md`, CHANGELOG section + version bump, tag `v0.5.0` | all | last |

Critical path: WP1 → WP2 → WP3(bonuses) → WP7. WP4 can start immediately.

## 6. Testing strategy

- **Fixtures (synthetic only).** A `season_fixture()` factory in
  `tests/conftest.py` generating N rounds of Classification CSVs (reusing
  the `classification_race_sample.csv` shape) with controlled grids, points
  columns (when the variant has them), retirements, a DSQ, and one
  "Le Mans" round — enough to exercise multipliers, drops, bonuses and
  status mapping deterministically. One extra fixture per real header
  variant the probe uncovers.
- **Offline unit tests.** `test_standings.py` grows preset coverage:
  drop-score selection (worst rounds, ties, fewer rounds than `drop`),
  multiplier alignment via `round_names`, pole/FL bonuses per class,
  `use_source_points`, backwards compatibility of every existing call.
  New `test_season.py` and `test_trends.py` run fully offline by
  monkeypatching `endurancepy.alkamel.client.download` (the canonical
  pattern in `tests/test_examples.py`), serving a fake portal index plus
  synthetic CSVs for a 3-round season.
- **Chart tests** in `test_plotting.py` behind
  `pytest.importorskip("plotly")`, as today.
- **Network integration** (`test_integration_network.py`, self-skipping):
  one new case — `get_season` on a short real season (e.g. ELMS, fewer and
  shorter races than WEC), assert every round loads, results carry the new
  columns, and `season.standings(points="elms_<year>", per_class=True)`
  matches the known official champion + point totals for at least one class.
- **Examples** — the title-fight notebook joins `examples/` and is executed
  offline in CI through the faked download layer (`test_examples.py`).

## 7. Risks & open questions

| # | Risk / question | Mitigation |
|---|---|---|
| R1 | **Points/grid absent from the Classification CSV** (the verified race header has neither). | Grid: fall back to the qualifying session's Classification (positions there *are* the grid, minus penalties). Points: leave `Points` empty from source and lean on the presets — `use_source_points` then simply has nothing to sum; documented honestly ("honest about the source"). |
| R2 | Per-series **drop-score subtleties** (which rounds are droppable, teams' vs drivers' drops differing, part-season entries). | `drop` stays a blunt "n worst round scores"; anything finer is out of scope (non-goal: rules engine) and documented per preset. |
| R3 | **Le Mans multiplier targeting** — matching `"Le Mans"` against `EventName` could hit "Le Mans Cup" style names or miss renames. | Substring match against the schedule's `EventName` with a logged notice of which round(s) matched; `round_multipliers` accepts a round number key as escape hatch. |
| R4 | **Per-driver standings** need crew explosion and per-driver drop rules. | Deferred; `by="Crew"` documented as the 0.5.0 granularity limit. |
| R5 | **IMSA portal drift** (`imsa.results.alkamelcloud.com` differs from the WEC/ELMS portals) may break season discovery. | WEC + ELMS are the exit-criteria series; IMSA is best-effort, probe findings decide. |
| R6 | **Superseason semantics** (`08_2018-2019` spans two years). | Already handled by `_SEASON_YEAR_RE` (starting year) and the explicit `season=` override on `get_season`, mirroring `get_event_schedule`. |
| R7 | Driver **categories/entry metadata simply not published** in CSV form (PDF-only entry lists). | Columns exist typed-but-empty; a PDF path is explicitly out of 0.5.0 scope (revisit with the `pdf` extra idea if demand shows). |
| R8 | Loading a full WEC season is slow/heavy on first run. | Sequential downloads through the existing rate-respecting client + cache; `Season.load(sessions=...)` loads only what is asked. |

## 8. Exit criteria (mirrors the roadmap)

- [ ] Probe findings documented; Classification parser exposes **grid,
      points, penalties, status** from source wherever the source has them,
      plus entry metadata columns (populated or honestly empty).
- [ ] `POINTS_PRESETS` for WEC / ELMS / IMSA (current year at minimum),
      including Le Mans multiplier, drop scores, pole/fastest-lap bonuses —
      all as configuration of `compute_standings`.
- [ ] `get_season(year, series)` loads a full season's races in one call,
      idempotent via the existing cache.
- [ ] Trend tables + `plot_standings_evolution` + season-form heatmap
      shipped with offline tests and gallery entries.
- [ ] **Reproduced final standings** for one full WEC season and one full
      ELMS season (all classes) from source data, recorded in
      `docs/test_plan_0.5.0.md`.
- [ ] Title-fight notebook in `examples/`, executed offline in CI.
- [ ] `CHANGELOG.md` 0.5.0 section + version bump; release per
      `RELEASING.md` (merge → tag `v0.5.0` → automatic publish).

---

*Living plan — amend as the probe findings land (WP1 updates §2/§3.1 before
WP2 starts).*
