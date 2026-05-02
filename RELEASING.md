# Releasing APICORE

## Preconditions

- Confirm the version in `pyproject.toml`.
- Ensure `uv.lock` is up to date.
- Ensure the working tree only contains intended release changes.

## Validate

```bash
uv sync --all-groups
uv run pytest -q
uv build
uv run --with twine twine check dist/*
```

## Publish

Publish to PyPI with a token-based workflow:

```bash
set UV_PUBLISH_TOKEN=pypi-***
uv publish
```

If you need TestPyPI instead:

```bash
set UV_PUBLISH_TOKEN=pypi-***
uv publish --publish-url https://test.pypi.org/legacy/
```

## Post-release

- Create a git tag matching the released version.
- Attach `dist/*` artifacts to the release if you also publish on GitHub.
- Update `CHANGELOG.md` for the next version.