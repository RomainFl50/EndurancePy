# Releasing

EndurancePy is published to [PyPI](https://pypi.org/) via GitHub Actions using
**Trusted Publishing** (OIDC) — no API token is stored in the repository.

## One-time setup (PyPI Trusted Publisher)

On PyPI, add a *trusted publisher* for the project (Account → Publishing, or the
project's *Settings → Publishing*) with:

- **Owner**: `RomainFl50`
- **Repository**: `EndurancePy`
- **Workflow**: `release.yml`
- **Environment**: `pypi`

(For the very first release you can create a "pending" publisher before the
project exists on PyPI.) Optionally protect the `pypi` GitHub Environment with
required reviewers.

## Cutting a release

1. Update [`CHANGELOG.md`](CHANGELOG.md): move `Unreleased` entries under a new
   `## [X.Y.Z] - YYYY-MM-DD` section and update the link references.
2. Bump `version` in [`pyproject.toml`](pyproject.toml).
3. Commit and merge to `main`.
4. Tag and push:

   ```bash
   git tag vX.Y.Z
   git push origin vX.Y.Z
   ```

5. The **release** workflow builds the sdist + wheel, runs `twine check`, and
   publishes to PyPI. (You can also dispatch it manually to build without
   publishing — the publish step only runs for `v*` tags.)

## Versioning

This project follows [Semantic Versioning](https://semver.org/). While the API is
stabilising (`0.x`), minor versions may include breaking changes.
