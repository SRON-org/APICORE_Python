<div align="center">

<image src="https://github.com/user-attachments/assets/3b85e1ef-35e3-4f95-bf5e-90ca7f8fae13" height="86"/>

# APICORE_Python

[![Version](https://img.shields.io/badge/version-2.0.0-green.svg)](VERSION)

APICORE access framework for Python

#### [Main Repo](https://github.com/SRON-org/APICORE)

</div>

## APICORE

High-performance APICORE parser and validator for APICORE v1 and v2.

A collaboration by [Little Tree Studio](https://github.com/Little-Tree-Studio) and [SRInternet Studio](https://github.com/SRInternet-Studio).

### Features

- Import name is `apicore`, while the published package name is `APICORE_Python`.
- Uses `orjson` for fast JSON decoding.
- Uses `ruamel.yaml` with `ruamel.yaml.clib` for YAML decoding.
- Keeps `msgspec` for fast TOML decoding.
- Supports APICORE v1 and v2 with a single API.
- Defaults to v2 when `APICORE_version` is omitted, unless you manually force `version="v1"`.
- Preserves custom v2 parameter fields in `Parameter.extra`.
- Includes a CLI validator for release pipelines and local checks.

### Install

```bash
uv add APICORE_Python
```

or

```bash
pip install APICORE_Python
```

### Quick Start

```python
from apicore import __version__, load, loads

print(__version__)

document = load("example.api.yaml")
print(document.apicore_version)

inline = loads("""
friendly_name: Demo
link: https://api.example.com/v2/generate
func: POST
parameters:
	- name: api_key
		type: string
		friendly_name: API Key
		value: ''
response:
	image:
		content_type: URL
		path: data.output.url
""", format="yaml")

forced_v1 = loads("""
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
""", version="v1")
```

### CLI

```bash
apicore-validate path/to/config.api.yaml
apicore-validate path/to/config.api.json --version v1
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

Full documentation is available on the [GitHub Wiki](https://github.com/SRON-org/APICORE_Python/wiki).
