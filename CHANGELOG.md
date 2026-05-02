# Changelog

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