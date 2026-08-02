[English](CONTRIBUTING.md) | [中文](CONTRIBUTING.zh-CN.md)

# Contributing To APICORE_Python

Thank you for helping improve APICORE_Python. Contributions may include bug
reports, parser fixes, validation improvements, tests, performance work, and
documentation corrections.

## Before You Start

- Search existing issues and pull requests before opening a duplicate.
- Keep each change focused on one problem. Discuss broad API changes or
  breaking behavior in an issue before implementation.
- Report suspected vulnerabilities privately as described in
  [SECURITY.md](SECURITY.md), not in a public issue.
- APICORE specification changes belong in the relevant specification repository
  first. This project should implement documented APICORE behavior rather than
  define a conflicting format independently.

## Development Setup

The project requires Python 3.12 or later and uses
[uv](https://docs.astral.sh/uv/) for dependency and environment management.

```bash
git clone https://github.com/SRON-org/APICORE_Python.git
cd APICORE_Python
uv sync --all-groups
```

Run the repository tools from the checkout when needed:

```bash
uv run python tools/cli.py path/to/config.api.yaml
uv run python tools/gui.py
```

The CLI and GUI are repository-only tools. They must not become installed
package modules or console-script entry points.

## Making Changes

- Follow the existing Python style and retain type annotations for public and
  internal interfaces.
- Keep the public import surface deliberate. New public APIs must be exported
  from `src/apicore/__init__.py` and covered by public API tests.
- Preserve APICORE v1, v2.0, and v2.1 compatibility unless the proposed change
  explicitly documents a breaking change.
- Return `ParseError` for decoding failures and `ValidationError` for invalid
  APICORE structures. Include a precise JSON-style path in validation messages
  where possible.
- Do not mutate caller-provided mappings passed to `parse()`.
- Treat configuration content as untrusted. Parser or tool changes must not
  execute `run` scripts, invoke configured URLs, reveal secret values, or switch
  YAML to an unsafe loader.
- Add or update tests for every behavior change and regression fix. Prefer a
  small fixture embedded in the relevant test over a large generated artifact.
- Update `README.md`, local `docs/` sources, and `CHANGELOG.md` when user-visible
  behavior, compatibility, or workflows change.
- Do not commit virtual environments, caches, build output, credentials, tokens,
  or unrelated generated files.

## Validation

Run the same core checks expected by the project before submitting a pull
request:

```bash
uvx ruff format --check .
uvx ruff check .
uv run pytest -q
uv build
```

Parser changes should be tested with all affected serialization formats and
APICORE versions. Packaging changes must retain these invariants:

- The wheel contains the core `apicore` library only.
- `tools/` is not included in the installed package.
- No `apicore-validate` or `apicore-gui` entry point is installed.

For release-related changes, also follow [RELEASING.md](RELEASING.md).

## Pull Requests

A pull request should:

- Explain the problem and the chosen solution.
- Reference the related issue or APICORE specification section when applicable.
- Describe compatibility, security, and performance effects.
- Include tests that fail without the fix and pass with it.
- List the validation commands that were run and disclose any checks that could
  not be completed.
- Avoid combining refactoring, dependency updates, formatting churn, and
  behavior changes unless they are inseparable.

Maintainers may request changes to preserve the package boundary, public API,
supported APICORE versions, or security model. A contribution is considered
accepted only after it has been reviewed and merged by a maintainer.

## License

By submitting a contribution, you agree that it may be distributed under the
terms of the project [LICENSE](LICENSE), and you confirm that you have the right
to submit the contributed material.