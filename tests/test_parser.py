from __future__ import annotations

import json

import pytest

from apicore import (
    Parameter,
    RequestConfig,
    ResponseConfig,
    ValidationError,
    __version__,
    load,
    loads,
    parse,
    resolve_i18n,
)
from apicore.models import ResponseImage

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


V2_1_JSON = r"""
{
  "$schema": "https://raw.githubusercontent.com/SRON-org/APICORE-2/refs/heads/main/APICORE.v2.Schema.json",
  "id": "superai-demo",
  "version": "2.1.0",
  "author": "SRInternet",
  "license": "MIT",
  "repository": "https://github.com/SRON-org/APICORE-2",
  "updated_at": "2026-08-01",
  "friendly_name": {"zh-CN": "绘图", "en-US": "Image Generator"},
  "intro": {"zh-CN": "异步绘图", "en-US": "Async image generation"},
  "link": "https://api.example.com/users/{{parameters.user_id}}/generate",
  "func": "POST",
  "APICORE_version": "2.1",
  "configs": {
    "request": {
      "body_type": "json",
      "body_template": {"prompt": "{{parameters.prompt}}"},
      "headers": {"Authorization": "Bearer {{parameters.api_key}}"},
      "timeout_ms": 15000
    },
    "polling": {
      "interval_ms": 2000,
      "timeout_ms": 120000,
      "check_link": "https://api.example.com/tasks/{{response.task_id}}",
      "status_path": "data.status",
      "success_value": "SUCCEEDED",
      "failed_value": ["FAILED", "CANCELLED"]
    }
  },
  "parameters": [
    {
      "name": "api_key", "type": "string", "friendly_name": "API Key",
      "value": "", "text_secret": true
    },
    {
      "name": "user_id", "type": "string", "friendly_name": "User",
      "value": "guest"
    },
    {
      "name": "prompt", "type": "string",
      "friendly_name": {"zh-CN": "描述", "en-US": "Prompt"}, "value": "cat"
    },
    {
      "name": "style", "type": "enum", "friendly_name": "Style",
      "options": ["realistic", "anime"],
      "friendly_options": ["Realistic", {"zh-CN": "动漫", "en-US": "Anime"}],
      "value": "realistic"
    },
    {
      "name": "advanced", "type": "boolean", "friendly_name": "Advanced",
      "value": false
    },
    {
      "name": "steps", "type": "integer", "friendly_name": "Steps",
      "value": 20, "min_value": 1, "max_value": 50,
      "show_if": {"parameter": "advanced", "equals": true}
    }
  ],
  "handlers": {
    "200": {"action": "response"},
    "400": {
      "action": "error",
      "message": {"zh-CN": "请求错误", "en-US": "Bad request"}
    },
    "default": {"action": "return"}
  },
  "response": {
    "media": {
      "type": "image", "content_type": "URL", "path": "data.output.url"
    },
    "image": {"content_type": "URL", "path": "legacy.image.url"},
    "others": [
      {
        "friendly_name": {"zh-CN": "详情", "en-US": "Details"},
        "data": [{"friendly_name": "Cost", "path": "data.cost"}]
      }
    ]
  }
}
"""


def test_loads_v1_json() -> None:
    document = loads(V1_JSON)
    assert document.apicore_version == "1.0"
    assert document.parameters[0].type == "integer"


def test_loads_retains_v2_0_when_version_and_v2_1_features_are_missing() -> None:
    document = loads(V2_YAML, format="yaml")
    assert document.apicore_version == "2.0"
    assert document.parameters[1].extra == {"precision": 2}
    assert document.configs is not None
    assert document.configs.request is not None
    assert (
        document.configs.request.headers["Authorization"]
        == "Bearer {{parameters.api_key}}"
    )


def test_invalid_parameter_reference_raises() -> None:
    bad = V2_YAML.replace("api_key", "missing_parameter", 1)
    with pytest.raises(ValidationError):
        loads(bad, format="yaml")


def test_binary_response_allows_empty_image_path() -> None:
    binary_yaml = V2_YAML.replace("content_type: URL", "content_type: BINARY").replace(
        "path: data.output.url", "path: ''"
    )
    document = loads(binary_yaml, format="yaml")
    assert document.response.image is not None
    assert document.response.image.content_type == "BINARY"
    assert document.response.image.path == ""


def test_disabled_parameter_allows_empty_friendly_name() -> None:
    disabled_json = V1_JSON.replace(
        '"friendly_name": "数量"', '"friendly_name": ""'
    ).replace('"split_str": null', '"split_str": null,\n      "enable": false')
    document = loads(disabled_json)
    assert document.parameters[0].enable is False
    assert document.parameters[0].friendly_name == ""


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
    assert __version__ == "2.1.0"


def test_loads_complete_v2_1_document() -> None:
    document = loads(V2_1_JSON)

    assert document.apicore_version == "2.1"
    assert document.schema_url is not None
    assert document.id == "superai-demo"
    assert document.friendly_name["zh-CN"] == "绘图"
    assert document.configs is not None
    assert document.configs.request is not None
    assert document.configs.request.body_type == "json"
    assert document.configs.request.body_template == {"prompt": "{{parameters.prompt}}"}
    assert document.configs.polling is not None
    assert document.configs.polling.success_value == "SUCCEEDED"
    assert document.parameters[3].options == ("realistic", "anime")
    assert document.parameters[3].value == "realistic"
    assert document.parameters[5].show_if is not None
    assert document.parameters[5].show_if.parameter == "advanced"
    assert document.response.media is not None
    assert document.response.media.type == "image"
    assert document.response.image is not None
    assert document.response.preferred_media is document.response.media
    assert document.handlers["400"].message == {
        "zh-CN": "请求错误",
        "en-US": "Bad request",
    }


def test_undeclared_document_with_v2_1_features_is_inferred_as_v2_1() -> None:
    document = loads(V2_1_JSON.replace('  "APICORE_version": "2.1",\n', ""))
    assert document.apicore_version == "2.1"


def test_undeclared_legacy_others_only_response_remains_v2_0() -> None:
    config = {
        "friendly_name": "Legacy details",
        "link": "https://api.example.com/details",
        "func": "GET",
        "parameters": [],
        "response": {
            "others": [
                {
                    "friendly_name": "Details",
                    "data": [{"friendly_name": "Cost", "path": "data.cost"}],
                }
            ]
        },
    }

    document = parse(config)
    assert document.apicore_version == "2.0"
    assert document.response.others[0].friendly_name == "Details"


def test_v2_family_override_accepts_v2_1() -> None:
    document = loads(V2_1_JSON, version="v2")
    assert document.apicore_version == "2.1"


def test_legacy_image_is_exposed_as_preferred_media() -> None:
    document = loads(V2_TOML, format="toml")
    assert document.response.preferred_media is not None
    assert document.response.preferred_media.type == "image"
    assert document.response.preferred_media.path == "data.output.url"


def test_exact_v2_1_override_rejects_v2_0() -> None:
    with pytest.raises(ValidationError):
        loads(V2_TOML, format="toml", version="2.1")


@pytest.mark.parametrize("version", ["2.0", "2.1"])
def test_exact_override_sets_version_for_undeclared_document(version: str) -> None:
    document = loads(V2_YAML, format="yaml", version=version)
    assert document.apicore_version == version


def test_parse_accepts_mapping_without_mutating_it() -> None:
    config = json.loads(V2_1_JSON)
    before = json.loads(json.dumps(config))
    document = parse(config)

    assert document.apicore_version == "2.1"
    assert config == before


def test_resolve_i18n_uses_locale_fallback_and_first_value() -> None:
    value = {"zh-CN": "绘图", "en-US": "Image Generator"}

    assert resolve_i18n("Plain", "zh-CN") == "Plain"
    assert resolve_i18n(value, "zh-CN") == "绘图"
    assert resolve_i18n(value, "ja-JP", fallback_locale="en-US") == "Image Generator"
    assert resolve_i18n(value, "ja-JP") == "绘图"


def test_resolve_i18n_rejects_empty_mapping() -> None:
    with pytest.raises(ValidationError, match="at least one locale"):
        resolve_i18n({}, "en-US")


def test_v2_1_enum_default_must_be_an_option() -> None:
    bad = V2_1_JSON.replace('"value": "realistic"', '"value": "missing"')
    with pytest.raises(ValidationError, match="must be present"):
        loads(bad)


def test_v2_1_show_if_target_must_exist() -> None:
    bad = V2_1_JSON.replace('"parameter": "advanced"', '"parameter": "missing"')
    with pytest.raises(ValidationError, match="unknown parameter"):
        loads(bad)


@pytest.mark.parametrize("status", ["99", "600"])
def test_handler_status_must_be_valid_http_code(status: str) -> None:
    bad = V2_1_JSON.replace('"400": {', f'"{status}": {{')
    with pytest.raises(ValidationError, match="100 to 599"):
        loads(bad)


@pytest.mark.parametrize("method", ["CONNECT", "TRACE"])
def test_unsupported_http_methods_are_rejected(method: str) -> None:
    bad = V2_1_JSON.replace('"func": "POST"', f'"func": "{method}"')
    with pytest.raises(ValidationError, match="uppercase HTTP method"):
        loads(bad)


@pytest.mark.parametrize("version", ["1.0", "2.0"])
@pytest.mark.parametrize("method", ["CONNECT", "TRACE"])
def test_legacy_versions_retain_all_standard_http_methods(
    version: str, method: str
) -> None:
    config = {
        "friendly_name": "Legacy",
        "link": "https://api.example.com/x",
        "func": method,
        "APICORE_version": version,
        "parameters": [],
        "response": {"image": {"content_type": "URL", "path": "data.url"}},
    }

    document = parse(config)
    assert document.func == method


@pytest.mark.parametrize(
    "body_template",
    [
        [{"id": "{{parameters.user_id}}"}],
        "{{parameters.user_id}}",
        1,
        True,
    ],
)
def test_v2_1_json_body_template_accepts_any_json_value(body_template: object) -> None:
    config = json.loads(V2_1_JSON)
    config["configs"]["request"]["body_template"] = body_template

    document = parse(config)
    assert document.configs is not None
    assert document.configs.request is not None
    assert document.configs.request.body_template == body_template


@pytest.mark.parametrize(
    ("parameter", "error"),
    [
        (
            {
                "name": "style",
                "type": "enum",
                "friendly_name": "Style",
                "options": ["a", "b"],
                "value": "a",
            },
            "options requires APICORE v2.1",
        ),
        (
            {
                "name": "detail",
                "type": "string",
                "friendly_name": "Detail",
                "value": "x",
                "show_if": {"parameter": "detail", "equals": "x"},
            },
            "show_if requires APICORE v2.1",
        ),
    ],
)
def test_v2_1_parameter_features_require_v2_1(
    parameter: dict[str, object], error: str
) -> None:
    config = {
        "friendly_name": "Legacy",
        "link": "https://api.example.com/x",
        "func": "POST",
        "APICORE_version": "2.0",
        "parameters": [parameter],
        "response": {"image": {"content_type": "URL", "path": "data.url"}},
    }
    with pytest.raises(ValidationError, match=error):
        loads(json.dumps(config))


def test_v2_1_media_requires_v2_1() -> None:
    config = {
        "friendly_name": "Legacy",
        "link": "https://api.example.com/x",
        "func": "GET",
        "APICORE_version": "2.0",
        "parameters": [],
        "response": {
            "media": {"type": "audio", "content_type": "URL", "path": "data.url"}
        },
    }
    with pytest.raises(ValidationError, match="requires APICORE v2.1"):
        loads(json.dumps(config))


def test_v2_1_response_requires_media_or_image() -> None:
    bad = V2_1_JSON.replace(
        '"media": {\n      "type": "image", "content_type": "URL", "path": "data.output.url"\n    },\n    "image": {"content_type": "URL", "path": "legacy.image.url"},',
        "",
    )
    with pytest.raises(ValidationError, match="media.*image"):
        loads(bad)


def test_url_interpolation_is_restricted_to_path_and_query() -> None:
    bad = V2_1_JSON.replace(
        "https://api.example.com/users/{{parameters.user_id}}/generate",
        "https://{{parameters.user_id}}/generate",
    )
    with pytest.raises(ValidationError, match="path or query"):
        loads(bad)


def test_main_url_rejects_response_interpolation() -> None:
    bad = V2_1_JSON.replace(
        "https://api.example.com/users/{{parameters.user_id}}/generate",
        "https://api.example.com/tasks/{{response.task_id}}",
    )
    with pytest.raises(ValidationError, match="parameters.name"):
        loads(bad)


def test_polling_url_rejects_parameter_interpolation() -> None:
    bad = V2_1_JSON.replace(
        "https://api.example.com/tasks/{{response.task_id}}",
        "https://api.example.com/tasks/{{parameters.user_id}}",
    )
    with pytest.raises(ValidationError, match="response.name"):
        loads(bad)


def test_url_rejects_fragment_interpolation() -> None:
    bad = V2_1_JSON.replace(
        "https://api.example.com/users/{{parameters.user_id}}/generate",
        "https://api.example.com/generate#{{parameters.user_id}}",
    )
    with pytest.raises(ValidationError, match="fragment"):
        loads(bad)


def test_url_rejects_malformed_parameter_interpolation() -> None:
    bad = V2_1_JSON.replace("{{parameters.user_id}}", "{{parameters.missing-name}}", 1)
    with pytest.raises(ValidationError, match="invalid interpolation"):
        loads(bad)


@pytest.mark.parametrize("status", ["0200", "00100"])
def test_v2_1_handler_status_rejects_leading_zeroes(status: str) -> None:
    bad = V2_1_JSON.replace('"400": {', f'"{status}": {{')
    with pytest.raises(ValidationError, match="three-digit"):
        loads(bad)


def test_yaml_handler_keys_cannot_collide_after_normalization() -> None:
    bad = V2_YAML.replace(
        "  '200':\n    action: response",
        "  200:\n    action: return\n  '200':\n    action: response",
    )
    with pytest.raises(ValidationError, match="duplicate handler"):
        loads(bad, format="yaml")


def test_pre_v2_1_model_positional_construction_is_preserved() -> None:
    parameter = Parameter(True, "count", "integer", True, 1, "Count", None, 0, 10, None)
    request = RequestConfig({"X-Test": "yes"}, 1000)
    image = ResponseImage("URL", "data.url")
    response = ResponseConfig(image, ())

    assert parameter.min_value == 0
    assert parameter.options is None
    assert request.headers == {"X-Test": "yes"}
    assert request.timeout_ms == 1000
    assert response.image is image
    assert response.media is None
