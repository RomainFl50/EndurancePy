# Contributing to EndurancePy

First off — thank you for taking the time to contribute! EndurancePy aims to do
for endurance racing (WEC, ELMS, Asian Le Mans Series, Le Mans Cup, IMSA) what
[FastF1](https://github.com/theOehrly/Fast-F1) did for Formula 1, and it is very
much a community effort.

This project is in an **early / design phase** — there is no runnable package
yet, only the design groundwork. That means there is a lot of high-impact work
available, and good first contributions are easy to find.

By participating, you agree to abide by our
[Code of Conduct](CODE_OF_CONDUCT.md).

---

## Ways to contribute

- **Code** — implement one of the milestones (parsers, cache, core objects…).
- **Documentation** — improve docs, examples, docstrings.
- **Test data** — help build small, shareable fixtures (see the legal note
  below — do **not** commit raw Al Kamel archives).
- **Issues** — report bugs, request a series/season, or propose an API design.
- **Review** — review open pull requests.

If you are unsure where to start, **open an issue** describing what you'd like to
work on, so we can avoid duplicated effort and agree on the approach before you
write code.

## Understand the design first

Before writing code, please read the design documents — they are the functional
and technical spec for the package:

- [`docs/analyse_fastf1.md`](docs/analyse_fastf1.md) — exhaustive inventory of
  FastF1's content and how each piece maps onto endurance / Al Kamel data.
- [`docs/plan_implementation.md`](docs/plan_implementation.md) — the
  implementation plan: package layout, target column schemas, parsing pipeline,
  derivation algorithms, cache design, milestones and test strategy.

The guiding principle: **mirror FastF1's API and content** wherever the
underlying public data exists.

## Development setup

> The package skeleton is being bootstrapped; once `pyproject.toml` lands, the
> setup below applies.

```bash
# 1. Fork and clone
git clone https://github.com/<your-username>/EndurancePy.git
cd EndurancePy

# 2. Create a virtual environment (Python 3.10+)
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Install in editable mode with dev extras
pip install -e ".[dev]"

# 4. (optional) install pre-commit hooks
pre-commit install
```

## Coding guidelines

- **Python 3.10+**, with type hints on public functions.
- **Formatting & linting**: [`ruff`](https://docs.astral.sh/ruff/)
  (`ruff format` + `ruff check`).
- **Type checking**: `mypy`.
- **Docstrings** on all public classes/functions (NumPy or Google style).
- **Mirror FastF1 naming** where it makes sense (`get_session`, `Session.load`,
  `Session.laps`, `pick_*`, `Cache`) so FastF1 users feel at home. Document any
  deliberate divergence (see the plan).
- Keep parsers **tolerant**: Al Kamel CSV headers drift across seasons/series —
  match columns by name, handle the BOM and leading-space header variants.

## Tests

- Use `pytest`. Run the suite with:
  ```bash
  pytest
  ```
- New parsing logic must come with tests.
- Prefer **small, synthetic fixtures** that reproduce the format (a couple of
  cars, two classes, a few laps, a pit stop, a caution period). **Do not commit
  real Al Kamel timing files** (see the legal note).
- Network-dependent tests must be marked (e.g. `@pytest.mark.network`) and stay
  off by default.

## Commit messages

Use clear, descriptive messages. We loosely follow
[Conventional Commits](https://www.conventionalcommits.org/), e.g.:

```
feat(alkamel): parse Analysis CSV into Laps
fix(timeparse): handle the 24: elapsed-time rollover
docs: clarify per-class position derivation
test(headers): cover the IMSA WithSections variant
```

## Pull request workflow

1. Create a topic branch from `main` (`feat/...`, `fix/...`, `docs/...`).
2. Make focused commits; keep PRs reasonably small and single-purpose.
3. Ensure `ruff`, `mypy` and `pytest` pass locally.
4. Fill in the pull request template and link any related issue.
5. Be responsive to review feedback. Maintainers may request changes before merge.

## ⚖️ Legal note (please read)

EndurancePy parses **publicly published** timing archives. **Al Kamel Systems
explicitly asserts ownership of its timing data and warns against
redistribution.** Therefore:

- **Never commit raw Al Kamel data** (CSV/PDF archives) to this repository, and
  do not bundle or republish it in any artifact.
- Test fixtures must be **synthetic** or otherwise clearly redistributable.
- Always respect each site's Terms of Service and `robots.txt`, identify your
  client honestly, and keep request rates reasonable (the cache exists partly
  for this reason).

Contributions that redistribute proprietary data will not be accepted.

## License

By contributing, you agree that your contributions will be licensed under the
project's [MIT License](LICENSE).
