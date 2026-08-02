<div align="center">

<image src="https://github.com/user-attachments/assets/3b85e1ef-35e3-4f95-bf5e-90ca7f8fae13" height="86"/>

# APICORE_Python

[![Version](https://img.shields.io/badge/version-2.1.0-green.svg)](https://pypi.org/project/APICORE-Python/)

APICORE access framework for Python

#### [Main Repo](https://github.com/SRON-org/APICORE)

</div>

## APICORE

High-performance APICORE parser and validator for APICORE v1, v2.0, and v2.1.

A collaboration by [Little Tree Studio](https://github.com/Little-Tree-Studio) and [SRInternet Studio](https://github.com/SRInternet-Studio).

### Features

- Import name is `apicore`, while the published package name is `APICORE_Python`.
- Uses `orjson` for fast JSON decoding.
- Uses `ruamel.yaml` with `ruamel.yaml.clib` for YAML decoding.
- Keeps `msgspec` for fast TOML decoding.
- Supports APICORE v1, v2.0, and v2.1 with a single API.
- Defaults to the latest supported specification, APICORE v2.1, when `APICORE_version` is omitted.
- Preserves custom v2 parameter fields in `Parameter.extra`.
- Supports v2.1 metadata, `$schema`, i18n UI strings, request body types, polling, and conditional parameters.
- Supports v2.1 enum `options` with a scalar default while retaining the v2.0 `friendly_value` form.
- Supports image, audio, video, text, Markdown, and file outputs through `response.media`.
- Exposes `response.preferred_media`, which prefers v2.1 `media` and adapts legacy `image` automatically.
- Keeps the published package focused on parsing and validation; no CLI or GUI modules are installed.
- Provides repository-only CLI and desktop validator tools under `tools/`.
- Exposes typed document models plus `APICoreError`, `ParseError`, and `ValidationError` for precise error handling.

### Install

```bash
uv add APICORE_Python
```

or

```bash
pip install APICORE_Python
```

Installation provides the `apicore` Python library only. It does not install
`apicore-validate` or `apicore-gui` commands.

### Quick Start

```python
from apicore import __version__, load, loads

print(__version__)

document = load("example.api.yaml")
print(document.apicore_version)

inline = loads(
    """
friendly_name: Demo
link: https://api.example.com/v2/generate
func: POST
APICORE_version: '2.1'
parameters:
  - name: style
    type: enum
    friendly_name:
      zh-CN: 风格
      en-US: Style
    options: [realistic, anime]
    friendly_options: [Realistic, Anime]
    value: realistic
response:
  media:
    type: image
    content_type: URL
    path: data.output.url
""",
    format="yaml",
)

forced_v1 = loads(
    """
{
	"friendly_name": "Legacy",
	"link": "https://api.example.com/legacy",
	"func": "POST",
	"APICORE_version": "1.0",
	"parameters": [],
	"response": {
		"image": {
			"content_type": "URL",
			"path": "data.image.url"
		}
	}
}
""",
    version="v1",
)
```

### Repository CLI Tool

From a repository checkout:

```bash
uv sync
uv run python tools/cli.py path/to/config.api.yaml
uv run python tools/cli.py path/to/config.api.json --version v1
uv run python tools/cli.py path/to/config.api.toml --version 2.1
```

### Repository Desktop Tool

```bash
uv sync
uv run python tools/gui.py
```

On Windows, start it without a console after synchronization with
`.venv\Scripts\pythonw.exe tools\gui.py`. Some Linux distributions require the
system `python3-tk` package.

The GUI validates multiple APICORE documents and displays v2.1 metadata,
localized parameters, media mappings, request bodies, polling, configs, and
handlers. Secret values are masked, and `run` handlers are marked as high risk.

### Error Handling

```python
from apicore import load
from apicore.errors import APICoreError, ParseError, ValidationError

try:
    doc = load("example.api.yaml")
except ParseError as exc:
    print(f"Syntax error: {exc}")
except ValidationError as exc:
    print(f"Schema error: {exc}")
except APICoreError as exc:
    print(f"APICORE error: {exc}")
```

### Benchmark

```bash
uv run python benchmarks/parse_benchmark.py
```

### Release Workflow

```bash
uv sync --all-groups
uv run pytest -q
uv build
uv run --with twine twine check dist/*
```

Detailed release steps are in [RELEASING.md](RELEASING.md).

### Documentation

Wiki documentation is published manually to the
[GitHub Wiki](https://github.com/SRON-org/APICORE_Python/wiki). The local
`docs/` upload sources are intentionally ignored by Git. The APICORE v2.1
specification and JSON Schema are maintained in
[APICORE-2](https://github.com/SRON-org/APICORE-2).
