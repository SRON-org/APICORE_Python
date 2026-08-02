# Changelog

## 2.1.0

### Added

- Added explicit APICORE v2.1 version detection while retaining v1 and v2.0 compatibility.
- Added v2.1 configuration metadata and `$schema` support.
- Added i18n language dictionaries for UI-facing names, descriptions, messages, and response labels.
- Added request `body_type` and `body_template`, asynchronous polling, and typed `show_if` parameter conditions.
- Added v2.1 enum `options`, `friendly_options`, and scalar default validation.
- Added generalized `response.media` support for image, audio, video, text, Markdown, and file outputs.
- Added `ResponseConfig.preferred_media` to apply `media`-over-`image` precedence while adapting legacy image configurations.
- Added `parse()` for decoded mappings and `resolve_i18n()` for localized UI values.
- Added repository-only CLI and GUI tools under `tools/`.
- Added Wiki-ready documentation under `docs/`.

### Changed

- Restricted HTTP methods and handler status codes to the APICORE v2.1 schema values.
- Extended the CLI with exact `2.0`/`2.1` selectors and clean file-system error handling.
- Extended GUI details for metadata, media, request bodies, polling, enum options, and conditional parameters.
- Masked secret parameter values in GUI details and marked `run` handlers as high risk.
- Updated the package version to 2.1.0.
- Changed missing `APICORE_version` behavior to use the latest supported specification, v2.1.

### Removed

- Removed `apicore.cli` and `apicore.gui` from the published library package.
- Removed the installed `apicore-validate` and `apicore-gui` entry points. Use `uv run python tools/cli.py` and `uv run python tools/gui.py` from a repository checkout instead.

## 2.0.0

2.0.0 is a full rewrite of the old 1.0.0 package line, which fully supported APICORE v1.

### Breaking Changes

- Replaced the legacy `APICORE` package layout and its APICORE v1-focused JSON loader with the new `src/apicore` package and functional parsing API.
- Standardized the public import surface around `load()`, `loads()`, `validate()`, typed document models, and explicit parser exceptions.
- Removed the old `setup.py` packaging flow in favor of the `pyproject.toml` + `uv` build workflow.

### Added

- Added first-class APICORE v1 and v2 parsing with automatic version detection and optional explicit version override.
- Added JSON, YAML, and TOML decoding support using `orjson`, `ruamel.yaml`, and `msgspec`.
- Added typed document, parameter, response, config, and handler models for validated parser output.
- Added the `apicore-validate` CLI entry point for local checks and release pipelines.
- Added the `apicore-gui` desktop validator for batch file and folder validation with detailed result inspection.
- Added benchmark, release, and pytest coverage files for local validation and packaging checks.

### Changed

- Defaulted documents without `APICORE_version` to APICORE v2 while preserving explicit v1 compatibility checks.
- Preserved unknown v2 parameter fields in `Parameter.extra` so custom UI metadata can survive validation.
- Tightened validation for HTTP methods, URLs, parameter references, handler actions, and config sections.
- Updated parameter validation so disabled parameters may use an empty `friendly_name`, while enabled parameters must still provide a non-empty label.
- Expanded GUI detail output to include parse timing, document metadata, parameter breakdowns, response mappings, configs, and handlers.

### Removed

- Removed the legacy `APICORE/core.py` implementation, parser plugin stubs, and the old sample config artifacts tied to the 1.0.0 structure.
