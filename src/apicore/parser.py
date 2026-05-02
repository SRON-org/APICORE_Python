from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from http import HTTPMethod
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import msgspec
import orjson
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from apicore.errors import ParseError, ValidationError
from apicore.models import (
    APICoreVersion,
    Configs,
    Document,
    FormatName,
    HandlerRule,
    Parameter,
    RateLimit,
    RequestConfig,
    ResponseConfig,
    ResponseDataField,
    ResponseGroup,
    ResponseImage,
    RetryPolicy,
    V1Document,
    V2Document,
)

_HTTP_METHODS = {method.value for method in HTTPMethod}
_V1_STANDARD_TYPES = {"integer", "boolean", "list", "string", "enum"}
_V2_STANDARD_TYPES = _V1_STANDARD_TYPES | {"number"}
_HANDLER_ACTIONS = {
    "response",
    "success",
    "warning",
    "error",
    "message",
    "browser",
    "run",
    "retry",
    "return",
}
_PARAMETER_REFERENCE_RE = re.compile(
    r"\{\{parameters\.(?P<name>[A-Za-z_][A-Za-z0-9_]*)\}\}"
)
_RATE_LIMIT_UNITS = {"sec", "min", "hour", "day"}
_YAML_DECODER = YAML(typ="safe", pure=False)


def load(
    path: str | Path,
    *,
    version: str | None = None,
    format: FormatName | None = None,
    encoding: str = "utf-8",
) -> Document:
    source_path = Path(path)
    raw = source_path.read_bytes()
    resolved_format = format or _infer_format_from_path(source_path)
    return loads(raw, version=version, format=resolved_format, encoding=encoding)


def loads(
    data: str | bytes,
    *,
    version: str | None = None,
    format: FormatName | None = None,
    encoding: str = "utf-8",
) -> Document:
    payload = data.encode(encoding) if isinstance(data, str) else data
    resolved_format = format or "json"
    raw = _decode_payload(payload, resolved_format)
    mapping = _require_mapping(raw, "$")
    target_version = _detect_version(mapping, version)
    if target_version == "v1":
        return _build_v1(mapping)
    return _build_v2(mapping)


def validate(
    path: str | Path,
    *,
    version: str | None = None,
    format: FormatName | None = None,
    encoding: str = "utf-8",
) -> Document:
    return load(path, version=version, format=format, encoding=encoding)


def _decode_payload(payload: bytes, format_name: FormatName) -> Any:
    try:
        if format_name == "json":
            return orjson.loads(payload)
        if format_name == "yaml":
            return _YAML_DECODER.load(payload)
        if format_name == "toml":
            return msgspec.toml.decode(payload)
    except ImportError as exc:
        raise ParseError(str(exc)) from exc
    except orjson.JSONDecodeError as exc:
        raise ParseError(str(exc)) from exc
    except YAMLError as exc:
        raise ParseError(str(exc)) from exc
    except msgspec.DecodeError as exc:
        raise ParseError(str(exc)) from exc
    raise ValidationError(f"Unsupported format: {format_name}")


def _infer_format_from_path(path: Path) -> FormatName:
    suffix = path.suffix.lower()
    if suffix == ".json":
        return "json"
    if suffix in {".yaml", ".yml"}:
        return "yaml"
    if suffix == ".toml":
        return "toml"
    raise ValidationError(
        f"Cannot infer file format from suffix '{path.suffix}'. "
        "Pass format='json', 'yaml', or 'toml'."
    )


def _detect_version(raw: Mapping[str, Any], requested: str | None) -> APICoreVersion:
    declared_raw = raw.get("APICORE_version")
    declared = _normalize_version(declared_raw) if declared_raw is not None else None
    if requested is not None:
        forced = _normalize_version(requested)
        if declared is not None and forced != declared:
            raise ValidationError(
                f"Requested version '{requested}' conflicts with APICORE_version '{declared_raw}'"
            )
        return forced
    if declared is None:
        return "v2"
    return declared


def _normalize_version(value: Any) -> APICoreVersion:
    if isinstance(value, (int, float)):
        normalized = str(value)
    else:
        normalized = _require_str(value, "$version").strip().lower()
    normalized = normalized.replace("apicore", "").replace(" ", "")
    if normalized in {"1", "1.0", "v1"}:
        return "v1"
    if normalized in {"2", "2.0", "v2"}:
        return "v2"
    raise ValidationError(f"Unsupported APICORE version: {value!r}")


def _build_v1(raw: Mapping[str, Any]) -> V1Document:
    if "configs" in raw or "handlers" in raw:
        raise ValidationError("APICORE v1 does not support 'configs' or 'handlers'")
    doc = V1Document(
        friendly_name=_require_non_empty_str(raw, "friendly_name", "$.friendly_name"),
        intro=_optional_str(raw.get("intro"), "$.intro"),
        icon=_optional_str(raw.get("icon"), "$.icon"),
        link=_validate_url(_require_non_empty_str(raw, "link", "$.link"), "$.link"),
        func=_validate_http_method(
            _require_non_empty_str(raw, "func", "$.func"), "$.func"
        ),
        apicore_version="1.0",
        parameters=_build_parameters(
            _require_sequence(raw.get("parameters"), "$.parameters"),
            method=_require_non_empty_str(raw, "func", "$.func"),
            version="v1",
            path="$.parameters",
        ),
        response=_build_response(
            _require_mapping(raw.get("response"), "$.response"), "$.response"
        ),
    )
    return doc


def _build_v2(raw: Mapping[str, Any]) -> V2Document:
    func = _validate_http_method(
        _require_non_empty_str(raw, "func", "$.func"), "$.func"
    )
    parameters = _build_parameters(
        _require_sequence(raw.get("parameters"), "$.parameters"),
        method=func,
        version="v2",
        path="$.parameters",
    )
    parameter_names = {parameter.name for parameter in parameters if parameter.name}
    _validate_parameter_references(raw, parameter_names)
    response = _build_response(
        _require_mapping(raw.get("response"), "$.response"), "$.response"
    )
    handlers = _build_handlers(
        raw.get("handlers"), response=response, path="$.handlers"
    )
    configs = _build_configs(raw.get("configs"), "$.configs")
    return V2Document(
        friendly_name=_require_non_empty_str(raw, "friendly_name", "$.friendly_name"),
        intro=_optional_str(raw.get("intro"), "$.intro"),
        icon=_optional_str(raw.get("icon"), "$.icon"),
        link=_validate_url(_require_non_empty_str(raw, "link", "$.link"), "$.link"),
        func=func,
        apicore_version="2.0",
        parameters=parameters,
        handlers=handlers,
        configs=configs,
        response=response,
    )


def _build_parameters(
    raw_items: Sequence[Any],
    *,
    method: str,
    version: APICoreVersion,
    path: str,
) -> tuple[Parameter, ...]:
    return tuple(
        _build_parameter(item, method=method, version=version, path=f"{path}[{index}]")
        for index, item in enumerate(raw_items)
    )


def _build_parameter(
    raw: Any, *, method: str, version: APICoreVersion, path: str
) -> Parameter:
    mapping = _require_mapping(raw, path)
    parameter_type = _require_non_empty_str(mapping, "type", f"{path}.type")
    friendly_name = _require_non_empty_str(
        mapping, "friendly_name", f"{path}.friendly_name"
    )
    enable = _optional_bool(mapping.get("enable"), f"{path}.enable", default=True)
    required = _optional_bool(mapping.get("required"), f"{path}.required", default=True)
    name = _optional_str(mapping.get("name"), f"{path}.name")
    tooltip = _optional_str(mapping.get("tooltip"), f"{path}.tooltip")
    placeholder = _optional_str(mapping.get("placeholder"), f"{path}.placeholder")
    text_secret = _optional_bool(
        mapping.get("text_secret"), f"{path}.text_secret", default=False
    )
    min_value = _optional_number(mapping.get("min_value"), f"{path}.min_value")
    max_value = _optional_number(mapping.get("max_value"), f"{path}.max_value")
    split_str = _optional_str(mapping.get("split_str"), f"{path}.split_str")
    if "value" not in mapping:
        raise ValidationError(f"{path}.value is required")
    value = mapping["value"]
    friendly_value = None
    if "friendly_value" in mapping and mapping["friendly_value"] is not None:
        friendly_value = _string_tuple(
            mapping["friendly_value"], f"{path}.friendly_value"
        )

    if method not in {"GET", "HEAD"} and not name:
        raise ValidationError(f"{path}.name is required when func is {method}")
    if min_value is not None and max_value is not None and min_value > max_value:
        raise ValidationError(
            f"{path}.min_value cannot be greater than {path}.max_value"
        )

    standard_types = _V1_STANDARD_TYPES if version == "v1" else _V2_STANDARD_TYPES
    if parameter_type in standard_types:
        _validate_standard_parameter(
            parameter_type=parameter_type,
            value=value,
            friendly_value=friendly_value,
            enable=enable,
            split_str=split_str,
            min_value=min_value,
            max_value=max_value,
            placeholder=placeholder,
            text_secret=text_secret,
            version=version,
            path=path,
        )

    extra = {
        key: item
        for key, item in mapping.items()
        if key
        not in {
            "enable",
            "name",
            "type",
            "required",
            "friendly_value",
            "value",
            "tooltip",
            "placeholder",
            "text_secret",
            "friendly_name",
            "min_value",
            "max_value",
            "split_str",
        }
    }
    return Parameter(
        enable=enable,
        name=name,
        type=parameter_type,
        required=required,
        value=value,
        friendly_name=friendly_name,
        friendly_value=friendly_value,
        min_value=min_value,
        max_value=max_value,
        split_str=split_str,
        tooltip=tooltip,
        placeholder=placeholder,
        text_secret=text_secret,
        extra=extra,
    )


def _validate_standard_parameter(
    *,
    parameter_type: str,
    value: Any,
    friendly_value: tuple[str, ...] | None,
    enable: bool,
    split_str: str | None,
    min_value: int | float | None,
    max_value: int | float | None,
    placeholder: str | None,
    text_secret: bool,
    version: APICoreVersion,
    path: str,
) -> None:
    if parameter_type == "integer":
        if not _is_int(value):
            raise ValidationError(f"{path}.value must be an integer")
        if version == "v1" and (min_value is None or max_value is None):
            raise ValidationError(
                f"{path}.min_value and {path}.max_value are required for v1 integer parameters"
            )
    elif parameter_type == "number":
        if not _is_number(value):
            raise ValidationError(f"{path}.value must be a number")
    elif parameter_type == "boolean":
        if not isinstance(value, bool):
            raise ValidationError(f"{path}.value must be a boolean")
    elif parameter_type == "list":
        if not _is_list_like(value):
            raise ValidationError(f"{path}.value must be a list")
        if not split_str:
            raise ValidationError(f"{path}.split_str is required for list parameters")
    elif parameter_type == "string":
        if not isinstance(value, str):
            raise ValidationError(f"{path}.value must be a string")
    elif parameter_type == "enum":
        if not _is_list_like(value):
            raise ValidationError(f"{path}.value must be a list for enum parameters")
        if not friendly_value:
            raise ValidationError(
                f"{path}.friendly_value is required for enum parameters"
            )
        if len(friendly_value) != len(value):
            raise ValidationError(
                f"{path}.friendly_value length must match {path}.value length"
            )
        if not enable:
            raise ValidationError(f"{path}.enable cannot be false for enum parameters")

    if placeholder is not None and parameter_type != "string":
        raise ValidationError(f"{path}.placeholder is only valid for string parameters")
    if text_secret and parameter_type != "string":
        raise ValidationError(f"{path}.text_secret is only valid for string parameters")
    if parameter_type not in {"integer", "number"} and (
        min_value is not None or max_value is not None
    ):
        raise ValidationError(
            f"{path}.min_value and {path}.max_value are only valid for integer/number parameters"
        )


def _build_response(raw: Mapping[str, Any], path: str) -> ResponseConfig:
    image = None
    if "image" in raw and raw["image"] is not None:
        image_mapping = _require_mapping(raw["image"], f"{path}.image")
        content_type = _require_non_empty_str(
            image_mapping, "content_type", f"{path}.image.content_type"
        )
        if content_type not in {"URL", "BINARY"}:
            raise ValidationError(
                f"{path}.image.content_type must be 'URL' or 'BINARY'"
            )
        image = ResponseImage(
            content_type=content_type,
            path=_require_non_empty_str(image_mapping, "path", f"{path}.image.path"),
            is_list=_optional_bool(
                image_mapping.get("is_list"), f"{path}.image.is_list", default=False
            ),
            is_base64=_optional_bool(
                image_mapping.get("is_base64"), f"{path}.image.is_base64", default=False
            ),
        )

    others: list[ResponseGroup] = []
    raw_others = raw.get("others")
    if raw_others is not None:
        for index, group in enumerate(_require_sequence(raw_others, f"{path}.others")):
            group_mapping = _require_mapping(group, f"{path}.others[{index}]")
            raw_data = _require_sequence(
                group_mapping.get("data"), f"{path}.others[{index}].data"
            )
            data_fields: list[ResponseDataField] = []
            for data_index, item in enumerate(raw_data):
                item_mapping = _require_mapping(
                    item, f"{path}.others[{index}].data[{data_index}]"
                )
                data_fields.append(
                    ResponseDataField(
                        friendly_name=_require_non_empty_str(
                            item_mapping,
                            "friendly_name",
                            f"{path}.others[{index}].data[{data_index}].friendly_name",
                        ),
                        path=_require_non_empty_str(
                            item_mapping,
                            "path",
                            f"{path}.others[{index}].data[{data_index}].path",
                        ),
                    )
                )
            others.append(
                ResponseGroup(
                    friendly_name=_require_non_empty_str(
                        group_mapping,
                        "friendly_name",
                        f"{path}.others[{index}].friendly_name",
                    ),
                    data=tuple(data_fields),
                )
            )

    if image is None and not others:
        raise ValidationError(f"{path} must define at least one of 'image' or 'others'")
    return ResponseConfig(image=image, others=tuple(others))


def _build_configs(raw: Any, path: str) -> Configs | None:
    if raw is None:
        return None
    mapping = _require_mapping(raw, path)
    request = None
    if "request" in mapping and mapping["request"] is not None:
        request_mapping = _require_mapping(mapping["request"], f"{path}.request")
        headers: dict[str, str] = {}
        raw_headers = request_mapping.get("headers")
        if raw_headers is not None:
            headers_mapping = _require_mapping(raw_headers, f"{path}.request.headers")
            headers = {
                _require_non_empty_string_value(
                    key, f"{path}.request.headers[{key!r}].key"
                ): _require_str(value, f"{path}.request.headers.{key}")
                for key, value in headers_mapping.items()
            }
        timeout_raw = request_mapping.get("timeout_ms", 30_000)
        if isinstance(timeout_raw, str):
            timeout_ms: int | str = _require_non_empty_str(
                {"timeout_ms": timeout_raw}, "timeout_ms", f"{path}.request.timeout_ms"
            )
        else:
            timeout_ms = _require_positive_int(
                timeout_raw, f"{path}.request.timeout_ms"
            )
        request = RequestConfig(headers=headers, timeout_ms=timeout_ms)

    retry = None
    if "retry" in mapping and mapping["retry"] is not None:
        retry_mapping = _require_mapping(mapping["retry"], f"{path}.retry")
        retry = RetryPolicy(
            count=_require_positive_int(
                retry_mapping.get("count", 3), f"{path}.retry.count"
            ),
            delay_ms=_require_non_negative_int(
                retry_mapping.get("delay_ms", 10_000), f"{path}.retry.delay_ms"
            ),
        )

    rate_limit = None
    if "rate_limit" in mapping and mapping["rate_limit"] is not None:
        rate_limit_mapping = _require_mapping(
            mapping["rate_limit"], f"{path}.rate_limit"
        )
        frequency = rate_limit_mapping.get("frequency")
        per = (
            _optional_str(rate_limit_mapping.get("per"), f"{path}.rate_limit.per")
            or "min"
        )
        if per not in _RATE_LIMIT_UNITS:
            raise ValidationError(
                f"{path}.rate_limit.per must be one of {sorted(_RATE_LIMIT_UNITS)}"
            )
        rate_limit = RateLimit(
            frequency=None
            if frequency is None
            else _require_positive_int(frequency, f"{path}.rate_limit.frequency"),
            per=per,
        )

    return Configs(request=request, retry=retry, rate_limit=rate_limit)


def _build_handlers(
    raw: Any, *, response: ResponseConfig, path: str
) -> dict[str, HandlerRule]:
    if raw is None:
        return {}
    mapping = _require_mapping(raw, path)
    handlers: dict[str, HandlerRule] = {}
    for key, item in mapping.items():
        handler_key = _require_str(key, f"{path}[key]")
        if handler_key != "default" and not handler_key.isdigit():
            raise ValidationError(
                f"{path}.{handler_key} must be an HTTP status code string or 'default'"
            )
        handler_mapping = _require_mapping(item, f"{path}.{handler_key}")
        action = _require_non_empty_str(
            handler_mapping, "action", f"{path}.{handler_key}.action"
        )
        if action not in _HANDLER_ACTIONS:
            raise ValidationError(
                f"{path}.{handler_key}.action has unsupported value '{action}'"
            )
        extract = {}
        if "extract" in handler_mapping and handler_mapping["extract"] is not None:
            extract_mapping = _require_mapping(
                handler_mapping["extract"], f"{path}.{handler_key}.extract"
            )
            extract = {
                _require_str(name, f"{path}.{handler_key}.extract[key]"): _require_str(
                    value, f"{path}.{handler_key}.extract.{name}"
                )
                for name, value in extract_mapping.items()
            }

        message = _optional_str(
            handler_mapping.get("message"), f"{path}.{handler_key}.message"
        )
        link = _optional_str(handler_mapping.get("link"), f"{path}.{handler_key}.link")
        script = _optional_str(
            handler_mapping.get("script"), f"{path}.{handler_key}.script"
        )
        front = _optional_bool(
            handler_mapping.get("front"), f"{path}.{handler_key}.front", default=False
        )
        count = None
        delay_ms = None
        if action == "response" and response.image is None and not response.others:
            raise ValidationError(
                f"{path}.{handler_key} uses action 'response' but response config is empty"
            )
        if action in {"success", "warning", "error", "message"} and not message:
            raise ValidationError(
                f"{path}.{handler_key}.message is required when action is '{action}'"
            )
        if action == "browser" and not link:
            raise ValidationError(
                f"{path}.{handler_key}.link is required when action is 'browser'"
            )
        if action == "run" and not script:
            raise ValidationError(
                f"{path}.{handler_key}.script is required when action is 'run'"
            )
        if action == "retry":
            count = _require_positive_int(
                handler_mapping.get("count"), f"{path}.{handler_key}.count"
            )
            delay_ms = _require_non_negative_int(
                handler_mapping.get("delay_ms"), f"{path}.{handler_key}.delay_ms"
            )

        handlers[handler_key] = HandlerRule(
            action=action,
            extract=extract,
            message=message,
            link=link,
            script=script,
            front=front,
            count=count,
            delay_ms=delay_ms,
        )
    return handlers


def _validate_parameter_references(
    raw: Mapping[str, Any], parameter_names: set[str]
) -> None:
    for path, text in _iter_strings(raw, "$"):
        for match in _PARAMETER_REFERENCE_RE.finditer(text):
            parameter_name = match.group("name")
            if parameter_name not in parameter_names:
                raise ValidationError(
                    f"Unknown parameter reference '{{{{parameters.{parameter_name}}}}}' at {path}"
                )


def _iter_strings(value: Any, path: str) -> Sequence[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    if isinstance(value, str):
        found.append((path, value))
    elif isinstance(value, Mapping):
        for key, item in value.items():
            found.extend(_iter_strings(item, f"{path}.{key}"))
    elif _is_list_like(value):
        for index, item in enumerate(value):
            found.extend(_iter_strings(item, f"{path}[{index}]"))
    return found


def _require_mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValidationError(f"{path} must be an object")
    return value


def _require_sequence(value: Any, path: str) -> Sequence[Any]:
    if not _is_list_like(value):
        raise ValidationError(f"{path} must be a list")
    return value


def _require_str(value: Any, path: str) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{path} must be a string")
    return value


def _require_non_empty_string_value(value: Any, path: str) -> str:
    text = _require_str(value, path)
    if not text.strip():
        raise ValidationError(f"{path} cannot be empty")
    return text


def _require_non_empty_str(mapping: Mapping[str, Any], key: str, path: str) -> str:
    if key not in mapping:
        raise ValidationError(f"{path} is required")
    value = _require_str(mapping[key], path)
    if not value.strip():
        raise ValidationError(f"{path} cannot be empty")
    return value


def _optional_str(value: Any, path: str) -> str | None:
    if value is None:
        return None
    return _require_str(value, path)


def _optional_bool(value: Any, path: str, *, default: bool) -> bool:
    if value is None:
        return default
    if not isinstance(value, bool):
        raise ValidationError(f"{path} must be a boolean")
    return value


def _optional_number(value: Any, path: str) -> int | float | None:
    if value is None:
        return None
    if not _is_number(value):
        raise ValidationError(f"{path} must be a number")
    return value


def _require_positive_int(value: Any, path: str) -> int:
    if not _is_int(value) or value <= 0:
        raise ValidationError(f"{path} must be a positive integer")
    return int(value)


def _require_non_negative_int(value: Any, path: str) -> int:
    if not _is_int(value) or value < 0:
        raise ValidationError(f"{path} must be a non-negative integer")
    return int(value)


def _validate_http_method(value: str, path: str) -> str:
    if value not in _HTTP_METHODS:
        raise ValidationError(f"{path} must be a valid uppercase HTTP method")
    return value


def _validate_url(value: str, path: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValidationError(f"{path} must be an absolute http/https URL")
    return value


def _string_tuple(value: Any, path: str) -> tuple[str, ...]:
    items = _require_sequence(value, path)
    return tuple(
        _require_str(item, f"{path}[{index}]") for index, item in enumerate(items)
    )


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number(value: Any) -> bool:
    return (isinstance(value, int) and not isinstance(value, bool)) or isinstance(
        value, float
    )


def _is_list_like(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(
        value, (str, bytes, bytearray)
    )
