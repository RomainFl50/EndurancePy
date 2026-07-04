# CLAUDE.md

EndurancePy loads endurance-racing timing & results data (WEC, ELMS, IMSA, …)
from the Al Kamel archives, with a FastF1-style API. `src/` layout, Hatchling,
Python ≥ 3.10.

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
- A merged-but-never-published milestone doesn't get a retroactive tag: fold
  it into the next release and say so in that release's CHANGELOG section
  (precedent: 0.3.0 shipped inside `v0.4.0`).
- Skipped version numbers are fine; silent republishes are not.
