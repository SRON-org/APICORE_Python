from __future__ import annotations

import pytest

from apicore import ValidationError, __version__, load, loads


V1_JSON = """
{
  "friendly_name": "Legacy API",
  "link": "https://api.example.com/generate",
  "func": "POST",
  "APICORE_version": "1.0",
  "parameters": [
    {
      "name": "count",
      "type": "integer",
      "required": true,
      "value": 3,
      "friendly_name": "数量",
      "min_value": 1,
      "max_value": 10,
      "split_str": null
    }
  ],
  "response": {
    "image": {
      "content_type": "URL",
      "path": "data.image.url"
    }
  }
}
"""


V2_YAML = """
friendly_name: Modern API
link: https://api.example.com/v2/generate
func: POST
configs:
  request:
    headers:
      Authorization: Bearer {{parameters.api_key}}
parameters:
  - name: api_key
    type: string
    required: true
    friendly_name: API Key
    value: ''
    text_secret: true
  - name: custom_mode
    type: custom-slider
    required: false
    friendly_name: 自定义模式
    value: 0.5
    precision: 2
handlers:
  '200':
    action: response
  default:
    action: error
    extract:
      raw: $body
    message: |-
      未知错误
      {{raw}}
response:
  image:
    content_type: URL
    path: data.output.url
"""


V2_TOML = """
friendly_name = "TOML API"
link = "https://api.example.com/v2/toml"
func = "POST"
APICORE_version = "2.0"

[[parameters]]
name = "api_key"
type = "string"
required = true
friendly_name = "API Key"
value = ""
text_secret = true

[handlers."200"]
action = "response"

[response.image]
content_type = "URL"
path = "data.output.url"
"""


def test_loads_v1_json() -> None:
    document = loads(V1_JSON)
    assert document.apicore_version == "1.0"
    assert document.parameters[0].type == "integer"


def test_loads_defaults_to_v2_when_version_missing() -> None:
    document = loads(V2_YAML, format="yaml")
    assert document.apicore_version == "2.0"
    assert document.parameters[1].extra == {"precision": 2}
    assert document.configs is not None
    assert document.configs.request is not None
    assert document.configs.request.headers["Authorization"] == "Bearer {{parameters.api_key}}"


def test_invalid_parameter_reference_raises() -> None:
    bad = V2_YAML.replace("api_key", "missing_parameter", 1)
    with pytest.raises(ValidationError):
        loads(bad, format="yaml")


def test_cli_compatible_file_loading(tmp_path) -> None:
    file_path = tmp_path / "example.api.yaml"
    file_path.write_text(V2_YAML, encoding="utf-8")
    document = load(file_path)
    assert document.friendly_name == "Modern API"


def test_loads_toml_v2() -> None:
  document = loads(V2_TOML, format="toml")
  assert document.apicore_version == "2.0"
  assert document.parameters[0].text_secret is True


def test_forced_version_conflict_raises() -> None:
  with pytest.raises(ValidationError):
    loads(V2_TOML, format="toml", version="v1")


def test_package_version_is_exposed() -> None:
  assert __version__ == "0.1.0"