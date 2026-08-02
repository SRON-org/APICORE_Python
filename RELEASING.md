[English](RELEASING.md) | [中文](RELEASING.zh-CN.md)

# Releasing APICORE

## Preconditions

- Confirm the version in `pyproject.toml`.
- Ensure `uv.lock` is up to date.
- Ensure the working tree only contains intended release changes.

## Validate

```bash
uv sync --all-groups
uvx ruff format --check .
uvx ruff check .
uv run pytest -q
uv build
uv run --with twine twine check dist/*
```

Inspect the built wheel and verify that it contains only the core `apicore`
library. It must not contain `apicore/cli.py`, `apicore/gui.py`, `tools/`, or
console-script entry points. Also smoke-test the repository tools:

```bash
uv run python tools/cli.py --help
uv run python -c "import runpy; runpy.run_path('tools/gui.py', run_name='gui_smoke')"
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