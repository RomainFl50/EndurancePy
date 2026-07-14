# Implementation plan — 0.7.0 "Reporting, exports & the docs site"

> Technical framing document for the 0.7.0 milestone (scope:
> [`ROADMAP.md`](../ROADMAP.md) § 0.7.0). Written against the 0.4.0 codebase;
> 0.5.0 / 0.6.0 land first, but nothing here depends on them except the
> championship-impact report section, which degrades gracefully (see §7).
> Style precedent: [`plan_implementation.md`](plan_implementation.md).

---

## 1. Goals & non-goals

**Goal:** make the library's output *shareable* — one command produces a
standalone HTML race report; every table exports to CSV/Parquet and comes back
intact; the docs live on a real site.

| In scope | Out of scope (roadmap non-goals) |
|---|---|
| `report(session)` API + `endurancepy report …` CLI | A hosted dashboard/service — we render *files*, we don't run servers |
| CSV/Parquet export + round-trip readers | New data or parsing work (that's 0.5.0/0.6.0) |
| MkDocs site, published on tagged releases | Docs versioning via `mike` (deferred; single "latest" is enough pre-1.0) |
| Static seaborn variants of the distribution charts | Static variants of the dense timelines (Gantt/trace/gap) — the appendix in `ROADMAP.md` explains why those stay interactive |
| Per-series palettes + wider team/manufacturer coverage | Per-driver colours (endurance non-goal since day one) |
| Animated position/gap evolution (Plotly frames) | Video/GIF rendering (users can screen-record; kaleido stays out) |

Conventions that bind every work package: lap times stay `Timedelta`; heavy
deps behind extras with a helpful `ImportError` (the `_import_go()` /
`setup_mpl()` pattern); helpers accept `Session | Laps | DataFrame` via the
`_laps_frame()` idiom; empty input → typed-but-empty output, never a raise;
no raw Al Kamel data in the repo — everything offline-testable through the
`endurancepy.alkamel.client.download` monkeypatch (`tests/test_examples.py`).

## 2. Exports — `endurancepy/export.py`

### 2.1 API shape: free functions, not methods

The roadmap says "every data object", but half of those objects are **plain
`DataFrame`s**: the strategy tables (`pit_stops`, `stint_summary`, …),
`weather_data`, `track_status` and `Standings` have no subclass we control (or
one too thin to matter). Methods on `Laps`/`SessionResults` would cover only a
third of the surface, and pandas already gives every frame `to_csv`/
`to_parquet` for the write side. The codebase style is also function-first
(`strategy.py`, `plotting.charts` all take `Session | Laps | DataFrame`).

So: **a small `export.py` module of free functions**, re-exported at top level.

```python
def export(
    data: Session | Laps | SessionResults | pd.DataFrame,
    path: str | os.PathLike[str],
    *,
    format: str | None = None,          # "csv" | "parquet"; default: from suffix
) -> Path: ...

def read_export(
    path: str | os.PathLike[str],
    *,
    dtypes: dict[str, str] | None = None,   # override/extend schema inference
) -> pd.DataFrame: ...
```

- `export(session, dir_path)` on a `Session` writes the bundle
  (`laps`, `results`, `weather`, `track_status`) into a directory, one file
  each; on a frame it writes one file. Parquet via the `pyarrow` core dep —
  no new dependency, same engine as the stage-2 cache.
- `read_export` restores dtypes from the **published schemas**: `_types.py`
  (`LAPS_COLUMNS`, `RESULTS_COLUMNS`, `WEATHER_COLUMNS`,
  `TRACK_STATUS_COLUMNS`) and the `strategy.py` `_*_DTYPES` dicts, matched by
  column set. The private strategy dtype dicts get promoted to a
  `SCHEMAS: dict[str, dict[str, str]]` registry in `_types.py` so export and
  strategy share one source of truth.

### 2.2 Round-trip guarantees

| Format | Guarantee | Mechanism |
|---|---|---|
| **Parquet** | Lossless: `assert_frame_equal` incl. dtypes (`timedelta64[ns]`, `Int64`, `string`, `boolean`, `float64`) | pyarrow preserves the extension/temporal types natively; nothing to do beyond tests |
| **CSV** | Value-equal after `read_export` for every published schema (test-enforced); dtype restoration needs the schema | Timedeltas serialise as pandas' `0 days 00:01:58.056000` text and parse back with `pd.to_timedelta`; `Int64`/`boolean` NA round-trip as empty cells via `astype` on read |

Documented CSV caveats (docs page "Exporting data"): a CSV without its schema
is just text — `read_export` on unknown column sets returns pandas defaults
plus a log warning; empty-string vs `<NA>` in `string` columns collapses to
`<NA>` (acceptable: Al Kamel sources never carry meaningful empty strings).
No sidecar metadata files — the schema registry keeps exports single-file.

## 3. The report — `endurancepy/report.py` + CLI

### 3.1 `report()` API and section model

```python
@dataclass(frozen=True)
class Section:
    id: str                 # "strategy", "race_trace", ...
    title: str
    build: Callable[[ReportContext], go.Figure | pd.DataFrame | str | None]
    # returning None (or an empty frame) skips the section silently

def report(
    session: Session,
    *,
    output: str | os.PathLike[str] | None = None,
    sections: Sequence[str | Section] | None = None,   # default: DEFAULT_SECTIONS
    title: str | None = None,          # default from Session repr metadata
    standings: Iterable[pd.DataFrame] | None = None,   # prior rounds' results
    theme: str = "dark",               # "dark" | "light"
) -> str | Path:                       # HTML string, or the written Path
```

`ReportContext` is a tiny holder (`session`, `laps`, `results`, `standings`,
`theme`) handed to each builder. Default sections, all reusing existing code:

| id | Content | Source |
|---|---|---|
| `header` | Event/session metadata, distance, class winners | `session`, `results` |
| `strategy` | Stint Gantt | `plotting.plot_strategy` |
| `race_trace` | Race trace + neutralisations shaded | `plot_race_trace` + `add_track_status` |
| `gaps` | Gap to class leader | `plot_gap(in_class=True)` |
| `pit_stops` | Bubble chart + the `pit_stops()` table | `plot_pit_stops`, `strategy.pit_stops` |
| `results` | Classification table per class | `session.results` |
| `championship` | Standings before/after this round | `compute_standings` — **only when `standings` given** (see §7), else skipped |

Custom sections are just `Section` instances in the `sections` list — no
plugin machinery.

### 3.2 Standalone HTML assembly

One self-contained file, openable from disk with no network:

- Each figure: `fig.to_html(full_html=False, include_plotlyjs=False)`.
- `plotly.offline.get_plotlyjs()` inlined **once** in `<head>` (~3.5 MB —
  accepted cost of "shareable"; documented).
- Tables: `DataFrame.to_html` after rendering `timedelta64` columns through
  `format_timedelta` (display-layer conversion, per convention).
- Page shell: an f-string/`string.Template` in `report.py` with a small
  embedded CSS block (dark/light per `theme`, matching `setup_mpl`'s palette).
  **No Jinja2** — one page shape doesn't justify a templating dependency.

### 3.3 CLI — `endurancepy/cli.py`

```
endurancepy report YEAR SERIES EVENT [SESSION]
    [--season SEASON_ID] [--output PATH] [--sections a,b,c]
    [--theme dark|light] [--cache DIR] [-v/--verbose]
endurancepy --version
```

- `argparse` subcommands (stdlib; leaves room for a future `endurancepy
  export …`). `SESSION` defaults to `"Race"`; `--output` defaults to a slug
  like `2024_WEC_Le-Mans_Race.html`.
- Entry point in `pyproject.toml`:

  ```toml
  [project.scripts]
  endurancepy = "endurancepy.cli:main"

  [project.optional-dependencies]
  report = ["plotly>=5.18"]           # superset alias of `interactive`
  ```

- `main(argv=None) -> int` so tests call it directly. `cli.py` imports only
  stdlib + `endurancepy` core at module level; `report.py` imports plotly
  lazily via the existing `_import_go()` pattern. Without plotly the CLI
  prints `error: the report needs plotly — pip install "endurancepy[report]"`
  and returns exit code 1 (no traceback). Discovery/download errors surface
  as one-line messages (+ traceback under `-v`).
- Year → Al Kamel season id resolution reuses what `Session.load(season=…)` /
  `default_season` and `list_seasons` already do; `--season` is the explicit
  escape hatch, exactly like the `season=` kwarg today.

## 4. Docs site

### 4.1 Tooling choice

| Option | For | Against |
|---|---|---|
| **MkDocs Material + mkdocstrings\[python] + mkdocs-jupyter** | Markdown-native (`docs/` and all guides already are); mkdocstrings reads our docstrings as-is; Material looks right out of the box; trivial CI | Weaker cross-referencing than Sphinx; pandas-subclass members need filtering |
| Sphinx (+ furo, autodoc, nbsphinx) | Gold-standard API refs; what FastF1 uses | rST friction, existing Markdown would need conversion or MyST glue; heavier setup |
| Jupyter Book | Notebook-first | Wrong emphasis — the site is API-ref + guides first, notebooks second |

**Recommendation: MkDocs Material.** The repo is already Markdown top to
bottom, and mkdocstrings' `filters`/`inherited_members: false` handles the one
real risk (drowning `Laps` in inherited `DataFrame` members). New `docs`
extra: `mkdocs-material`, `mkdocstrings[python]`, `mkdocs-jupyter`.

Site layout (`mkdocs.yml` at repo root, `docs_dir: docs`): Home (from
README) · Getting started (`usage.md`, reworked) · Guides (plotting gallery —
absorbing `plotting.md` —, strategy tables, exporting, reports & CLI) ·
Examples (executed notebooks) · API reference (mkdocstrings pages per module)
· Changelog/Roadmap (includes). Internal notes (`analyse_fastf1.md`,
`plan_*.md`, `test_plan_*.md`) stay in `docs/` but are excluded via
`exclude_docs` — they remain design documents, not site content.

### 4.2 Executing notebooks offline in CI

Same philosophy as `tests/test_examples.py`, adapted to the kernel boundary
(a monkeypatch in the build process doesn't reach the notebook's kernel):

- A fake-portal helper factored out of `test_examples.py` into
  `tests/_offline_portal.py` (fixtures stay synthetic, in `tests/fixtures/`).
- CI sets `IPYTHONDIR=docs/.ipython`; its
  `profile_default/startup/00_offline_portal.py` installs the fake `download`
  and a temp cache **only when `ENDURANCEPY_DOCS_OFFLINE=1`** — notebooks stay
  unmodified and still run live for users.
- `docs/execute_notebooks.py` (nbclient) pre-executes `examples/*.ipynb` into
  `docs/examples/`; `mkdocs-jupyter` renders with `execute: false`. Two-step
  keeps `mkdocs build --strict` fast and deterministic.

### 4.3 Publishing flow

New `.github/workflows/docs.yml`, sibling of `release.yml`:

- `on: push: tags: ["v*"]` + `workflow_dispatch` → build (notebooks + `mkdocs
  build --strict`) → deploy via `actions/upload-pages-artifact` +
  `actions/deploy-pages` (`pages: write`, `id-token: write`; no branch juggling).
- The same build job (minus deploy) runs on PRs touching `docs/**`,
  `examples/**`, `mkdocs.yml` or `src/**` docstrings — the docs build becomes
  a CI check before it can break a release.
- One-time repo setting: Pages source = GitHub Actions. Then update the
  `Documentation` URL in `pyproject.toml` to the Pages URL.

## 5. Static seaborn path & per-series palettes

### 5.1 `plotting/static.py`

Seaborn variants of the **distribution** charts only (the timelines stay
Plotly, per the roadmap appendix): `plot_pace`, `plot_driver_comparison`,
`plot_top_speeds`, each returning `(fig, ax)` (pandas-first principle:
"helpers return them (or `(fig, ax)`)"). Same names as `charts.py`, namespaced
by module — `from endurancepy.plotting import static; static.plot_pace(...)` —
so no `_mpl` suffix pollution and no ambiguous re-export in
`plotting/__init__` (which keeps exporting the Plotly set unchanged).

Built on the existing `setup_mpl()` + `format_time_axis()` (that was their
stated purpose in `style.py`); class colours from `colors.py` via seaborn
`palette=` dicts. Dependency guard mirrors `_import_go()`: seaborn imported
inside functions, `ImportError` says `pip install "endurancepy[plot]"`;
`plot` extra grows `seaborn>=0.13` (matplotlib comes with it).

### 5.2 Per-series palettes — `plotting/colors.py`

Today one flat `CLASS_COLORS` serves all series, so IMSA GTP and WEC Hypercar
can't diverge. Change, backward compatibly:

- `SERIES_CLASS_COLORS: dict[str, dict[str, str]]` overlay keyed by series
  name (`"IMSA"`, `"WEC"`, `"ELMS"`, …); lookup order: series overlay → global
  `CLASS_COLORS` → `DEFAULT_COLOR`.
- `get_class_color(name, series=None)` and `get_car_style(car, class_name,
  series=None)` grow an optional keyword; existing calls unchanged. Chart
  helpers pass `session.series.name` through when the source is a `Session`.
- Team/manufacturer coverage widened for the 2024–2026 entry lists (Isotta,
  Genesis, Vanwall, Glickenhaus historical, IMSA GTD teams, LMP2 field). Pure
  data PR — continuous-maintenance category, cheap to review.

## 6. Animated evolution charts — honest scope

`charts.py` gains `plot_position_animation(source, *, in_class=False, step=1)`
and `plot_gap_animation(...)` using Plotly frames + play/slider controls.

The physics of frames: one frame per lap × one trace per car. A 24 h WEC race
is ~380 laps × 62 cars ≈ 24 k frame-trace payloads — tens of MB of JSON and a
choppy player; frames don't combine with `Scattergl`. So, deliberately:

- `step=` subsamples laps; when `laps/step` exceeds a threshold (~150 frames)
  the helpers **auto-stride and log** what they did, instead of emitting an
  unusable figure.
- Positioning in docs: "6 h fields and single-class views animate well; for a
  full 24 h field, filter (`pick_classes`) or stride". Not a report section by
  default (file size), but addable as a custom `Section`.

## 7. Interaction with 0.5.0 / 0.6.0

0.7.0 is being planned while 0.5.0/0.6.0 are unshipped; only one touchpoint:

- **Championship impact section** consumes standings. Design against what
  exists **today** (`compute_standings` over an explicit list of
  `SessionResults`): `report(..., standings=[r1_results, r2_results, ...])` /
  CLI `--standings` pointing at exported results files (dogfooding §2). When
  0.5.0's season loader + series presets land, the CLI grows a
  `--championship` convenience that fetches prior rounds itself — an additive
  change. **No standings given → section skipped, report still valid.**
- 0.6.0's chart upgrades (pit durations on the Gantt, interval engine v2)
  flow into the report for free since sections call the same helpers.

## 8. Module-by-module change list

| File | Change |
|---|---|
| `src/endurancepy/export.py` | **New** — `export`, `read_export`, schema-registry lookup |
| `src/endurancepy/_types.py` | Add `SCHEMAS` registry; strategy dtype dicts registered here |
| `src/endurancepy/strategy.py` | Point `_*_DTYPES` at the shared registry (no behaviour change) |
| `src/endurancepy/report.py` | **New** — `report`, `Section`, `DEFAULT_SECTIONS`, HTML shell |
| `src/endurancepy/cli.py` | **New** — argparse `main`, `report` subcommand |
| `src/endurancepy/__init__.py` | Re-export `export`, `read_export`, `report` |
| `src/endurancepy/plotting/static.py` | **New** — seaborn `plot_pace` / `plot_driver_comparison` / `plot_top_speeds` |
| `src/endurancepy/plotting/colors.py` | `SERIES_CLASS_COLORS`, `series=` kwargs, coverage widening |
| `src/endurancepy/plotting/charts.py` | `series=` pass-through; `plot_position_animation`, `plot_gap_animation` |
| `pyproject.toml` | `[project.scripts]`; `report` extra; seaborn into `plot`; `docs` extra; Pages URL |
| `mkdocs.yml`, `docs/` site pages, `docs/.ipython/`, `docs/execute_notebooks.py` | **New** — site scaffolding (`plotting.md` absorbed into the gallery guide) |
| `.github/workflows/docs.yml` | **New** — build on PR, build+deploy on `v*` tag |
| `tests/_offline_portal.py` | **New** — fake portal factored out of `test_examples.py` |
| `tests/test_export.py`, `tests/test_report.py`, `tests/test_cli.py` | **New** suites (§10) |
| `examples/report_example.py`, `examples/test_plan_0_7_0.ipynb` | **New** — wired into `test_examples.py` / the manual plan |
| `docs/test_plan_0.7.0.md` | **New** — manual plan vs a real race |
| `CHANGELOG.md`, `ROADMAP.md`, `README.md` | Per-PR updates (convention); README gets the CLI one-liner + docs badge |

## 9. Work breakdown — PR-sized packages

| WP | Content | Depends on | Parallel? |
|---|---|---|---|
| **WP1** | Exports: `export.py`, `SCHEMAS` registry, round-trip tests, "Exporting data" guide | — | yes |
| **WP2** | Per-series palettes + coverage (`colors.py`, `charts.py` pass-through) | — | yes |
| **WP3** | Static seaborn path (`plotting/static.py`, `plot` extra, tests) | — | yes |
| **WP4** | Animated charts (`charts.py`, stride guard, tests) | — | yes |
| **WP5** | `report()` + sections + HTML shell (`report.py`, tests, example script) | WP2 (palettes in figures); championship section per §7 | after WP2 |
| **WP6** | CLI + console script + `report` extra (`cli.py`, `pyproject.toml`, tests) | WP5 | after WP5 |
| **WP7** | Docs site: mkdocs scaffold, offline notebook execution, `docs.yml`, gallery absorbing `plotting.md` | — (content PRs for WP1–6 pages follow their WPs) | yes |
| **WP8** | Release: `test_plan_0.7.0.md` run vs a real race, notebook, CHANGELOG cut, version bump | all | last |

Critical path: WP2 → WP5 → WP6 → WP8. WP1, WP3, WP4, WP7 are independent of
it and of each other. Nothing blocks on 0.5.0/0.6.0 (§7); if 0.5.0 has shipped
by WP6, the `--championship` convenience joins WP6, otherwise it's a fast
follow.

## 10. Testing strategy

All offline, per the repo's cardinal rule (no Al Kamel data; monkeypatch
`endurancepy.alkamel.client.download`):

- **Report** (`test_report.py`, `pytest.importorskip("plotly")`): using the
  shared fake-session fixture — generate to a tmp path; assert one file,
  contains each default section id, contains the inlined plotly.js (no
  `cdn.plot.ly`/`http` references), skips `championship` without standings and
  renders it with; `sections=` selection honoured; builder returning
  empty frame → section absent, report still written.
- **CLI** (`test_cli.py`): call `main([...])` with the download monkeypatch —
  exit 0 + file written; unknown event → exit 1 with a one-line message;
  plotly-missing path tested by masking the import (`monkeypatch.setitem
  (sys.modules, "plotly", None)`); `--version` prints `__version__`. Plus one
  `[project.scripts]` smoke test in the manual plan (entry points don't
  resolve from an editable test env reliably enough for CI to assert more).
- **Exports** (`test_export.py`, no optional deps): for every schema in
  `SCHEMAS`, build a synthetic frame with NAs in every nullable column →
  parquet round-trip `assert_frame_equal` exact; CSV round-trip
  `assert_frame_equal` after `read_export`; `Session` bundle export writes
  the four files; unknown-schema CSV warns and still reads.
- **Static/animated charts**: extend `test_plotting.py` under
  `importorskip("seaborn")` / `importorskip("plotly")` — figure returned,
  stride guard kicks in above the frame threshold.
- **Docs build in CI**: the `docs.yml` PR-path job is itself the test —
  `ENDURANCEPY_DOCS_OFFLINE=1` notebook execution + `mkdocs build --strict`
  (strict turns broken links/refs into failures), no network.
- **Examples**: `report_example.py` joins the `test_examples.py` harness.

## 11. Risks & open questions

| Subject | Risk | Mitigation |
|---|---|---|
| Report file size | plotly.js inline (~3.5 MB) + per-figure JSON; a 24 h field could reach 15–20 MB | Accept the baseline (standalone was the point); downsample hover-only data where cheap; measure in the manual plan; document |
| Plotly frames performance | Unusable animation on full 24 h fields | Auto-stride + log (§6); documented guidance; not in the default report |
| mkdocstrings vs pandas subclasses | API pages drowned in inherited `DataFrame` members | `inherited_members: false` + filters; reviewed page-by-page in WP7 |
| Kernel-boundary faking | IPython-startup hook silently not applying → notebooks hit the network in CI | Startup script asserts and prints when active; CI runs with no proxy so any real request fails loudly |
| CSV round-trip edge cases | Locale/Excel mangling of `0 days 00:01:58.056000` re-imports | Guarantee applies to `read_export`, not third-party tools; Parquet is the documented fidelity format |
| Console-script name collision | `endurancepy` binary vs package name confusion on `python -m` | Also ship `__main__.py` so `python -m endurancepy` works identically |
| Pages setup | Needs a repo-settings change (Actions as Pages source) outside the PR | Called out in WP7's PR description + RELEASING.md note |
| Open: season auto-resolution | Mapping bare `YEAR` to the Al Kamel season id must work for the CLI's headline UX | Reuse `default_season`/`list_seasons`; `--season` escape hatch; verify across series in the manual plan |
| Open: `report` extra vs `interactive` | Two extras pulling the same plotly | Keep both; `report` is the user-facing name in error messages; revisit merging at the 0.9.0 API review |

## 12. Exit criteria (mirrors the roadmap)

- [ ] `pip install "endurancepy[report]" && endurancepy report 2024 WEC "Le Mans"`
      produces one standalone HTML a race fan would share (opens from disk,
      offline; strategy Gantt, race trace, gaps, pit stops, results;
      championship impact when standings are supplied/available).
- [ ] `export`/`read_export` round-trip `Laps`, `SessionResults`, weather,
      track status and every strategy table through CSV and Parquet
      (Parquet dtype-exact), test-enforced.
- [ ] Docs site live on GitHub Pages: API reference, guides, plotting gallery,
      executed notebooks — built offline in CI, deployed by the `v0.7.0` tag.
- [ ] Static seaborn variants (`static.plot_pace`, `static.plot_driver_comparison`,
      `static.plot_top_speeds`) on `setup_mpl` + `format_time_axis`.
- [ ] Per-series palettes in effect (IMSA vs WEC/ELMS class colours) with
      widened team/manufacturer coverage.
- [ ] Animated position/gap evolution shipped with the documented stride guard.
- [ ] `docs/test_plan_0.7.0.md` written and executed against a real race;
      CHANGELOG cut + version bump per `RELEASING.md`.

---

*Living plan — amend as work packages land. Code starts at WP1.*
