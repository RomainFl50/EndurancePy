# CLAUDE.md

EndurancePy loads endurance-racing timing & results data (WEC, ELMS, IMSA, …)
from the Al Kamel archives, with a FastF1-style API. `src/` layout, Hatchling,
Python ≥ 3.10.

## Repository map

```
src/endurancepy/
  core.py            Session / Laps / Lap / SessionResults data objects; the
                     pick_* filters (pick_cars, pick_classes, pick_fastest, …)
  alkamel/           the portal-specific layer:
    client.py          results-tree URL building + cache-aware download
    discovery.py       season/event/session resolution (fuzzy-matched indexes)
    analysis.py        Analysis CSV -> Laps — the core parser (stints, pit
                       in/out, positions, gaps, Hour, PitTime)
    classification.py  race Classification CSV -> SessionResults
    weather.py         Weather CSV -> weather_data
    timeparse.py       tolerant duration parsing (SS.mmm … H:MM:SS.mmm, >24h)
    headers.py         tolerant Al Kamel CSV reading (BOM, stray spaces, …)
  strategy.py        race-craft tables: pit_stops, stint_summary,
                     driver_summary, lead_changes, battles, time_lost,
                     fuel_corrected
  plotting/          package: colors.py (class/manufacturer/team palettes),
                     style.py (matplotlib setup + lap-time axis), charts.py
                     (interactive Plotly figures + add_track_status /
                     add_day_night overlays)
  events.py          EventSchedule / Event (get_sessions, get_dates, get_race)
  results.py         SessionResults derivation from the laps
  standings.py       compute_standings (points across rounds)
  track_status.py    flag timeline from the laps
  cache.py           two-stage cache: raw HTTP (requests-cache/SQLite) +
                     parsed DataFrames (Parquet), namespaced by PARSER_VERSION
tests/               offline suite + synthetic fixtures;
                     test_integration_network.py is network-marked (self-skips)
examples/            network-based scripts & notebooks, executed offline in CI
                     via the faked download layer (test_examples.py)
docs/                design notes (analyse_fastf1.md), plotting gallery,
                     per-milestone manual test plans (test_plan_<version>.md)
ROADMAP.md           milestone planning; CHANGELOG.md follows Keep a Changelog
```

## Commands

```bash
pip install -e ".[dev,interactive,plot]"   # dev install (plotly + matplotlib extras)
python -m pytest -q                        # full suite; network tests self-skip offline
python -m ruff format . && python -m ruff check .   # ruff also lints notebooks (.ipynb)
python -m mypy                             # targets 3.12 (see pyproject comment)
```

## Conventions

- Lap/sector durations stay `pandas.Timedelta` (FastF1 parity); human-readable
  rendering is a display concern (`format_laptime` / `format_timedelta`).
- **No raw Al Kamel data in the repo.** Fixtures are synthetic; tests and the
  examples run offline by monkeypatching `endurancepy.alkamel.client.download`
  (see `tests/test_examples.py` for the canonical pattern).
- Analysis tables (`strategy.py`) accept a `Session`, a `Laps` or a plain
  `DataFrame`, and return typed-but-empty DataFrames instead of raising when
  the input has nothing to say.
- Chart tests guard optional deps with `pytest.importorskip("plotly")` (CI
  installs only `.[dev]`).
- New user-facing work: update `CHANGELOG.md` (under `## [Unreleased]`) and
  `ROADMAP.md` in the same PR.

## Release methodology (merge → tag → publish)

Generic procedure for every release; `RELEASING.md` is the reference.

1. **Validate before merging.** CI green on the release PR; for a feature
   milestone, run the corresponding manual test plan against a real race
   (e.g. `docs/test_plan_<version>.md` + its notebook in `examples/`).
2. **Cut the release notes in the same PR** as the version bump: move the
   `## [Unreleased]` entries under `## [X.Y.Z] - YYYY-MM-DD`, update the
   compare links at the bottom, bump `version` in `pyproject.toml`. Leave an
   empty `## [Unreleased]` section for the next cycle.
3. **Merge to `main`.** The tag must point at a `main` commit that contains
   the bumped version — the wheel is built from the tagged commit.
4. **Tag and push:**

   ```bash
   git checkout main && git pull origin main
   git tag vX.Y.Z && git push origin vX.Y.Z
   ```

5. **Publishing is automatic.** The `v*` tag triggers
   `.github/workflows/release.yml`: build sdist + wheel, `twine check`, then
   PyPI via Trusted Publishing (OIDC, GitHub environment `pypi` — no token).
6. **Verify:** the PyPI page shows the new version and
   `pip install --upgrade endurancepy` imports with the right `__version__`.
   Optionally create the GitHub Release from the tag with the CHANGELOG section.

Rules:

- **Never move or reuse a pushed tag** — if the release is broken, fix on
  `main` and cut the next patch version (PyPI refuses reused versions anyway).
- A merged-but-never-published milestone **keeps its own dated CHANGELOG
  section** (dated from its merge to `main`, compare-link on the merge commit),
  but gets no retroactive tag or PyPI upload — it first ships in the next
  published version, and both sections cross-reference each other
  (precedent: 0.3.0, first shipped in `v0.4.0`).
- Skipped tags are fine; silent republishes are not.
