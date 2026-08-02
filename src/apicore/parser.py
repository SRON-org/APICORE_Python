from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse

import msgspec
import orjson
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from apicore.errors import ParseError, ValidationError
from apicore.models import (
    APICoreFamily,
    APICoreVersion,
    Configs,
    Document,
    FormatName,
    HandlerRule,
    I18nString,
    Parameter,
    PollingConfig,
    RateLimit,
    RequestConfig,
    ResponseConfig,
    ResponseDataField,
    ResponseGroup,
    ResponseImage,
    ResponseMedia,
    RetryPolicy,
    ShowIf,
    V1Document,
    V2Document,
    VersionSelector,
)

_HTTP_METHODS = {"GET", "POST", "PUT", "DELETE", "HEAD", "PATCH", "OPTIONS"}
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
_BODY_TYPES = {"json", "form-data", "x-www-form-urlencoded", "raw"}
_MEDIA_TYPES = {"image", "audio", "video", "text", "markdown", "file"}
_LOCALE_RE = re.compile(r"^[a-z]{2}(?:-[A-Z]{2})?$")
_YAML_DECODER = YAML(typ="safe", pure=False)


def load(
    path: str | Path,
    *,
    version: VersionSelector | None = None,
    format: FormatName | None = None,
    encoding: str = "utf-8",
) -> Document:
    """Load and validate an APICORE configuration file.

    The input format is inferred from the filename unless ``format`` is supplied.
    Documents without ``APICORE_version`` use the latest supported version, 2.1.
    Filesystem errors are propagated unchanged; decoding and schema failures raise
    :class:`ParseError` and :class:`ValidationError` respectively.
    """
    source_path = Path(path)
    raw = source_path.read_bytes()
    resolved_format = format or _infer_format_from_path(source_path)
    return loads(raw, version=version, format=resolved_format, encoding=encoding)


def loads(
    data: str | bytes,
    *,
    version: VersionSelector | None = None,
    format: FormatName | None = None,
    encoding: str = "utf-8",
) -> Document:
    """Decode and validate an APICORE document from text or bytes.

    ``format`` defaults to ``"json"``. Text input is encoded with ``encoding``
    before decoding. Documents without an explicit version use APICORE 2.1.
    """
    payload = data.encode(encoding) if isinstance(data, str) else data
    resolved_format = format or "json"
    raw = _decode_payload(payload, resolved_format)
    return parse(raw, version=version)


def parse(
    data: Mapping[str, Any], *, version: VersionSelector | None = None
) -> Document:
    """Validate an already decoded APICORE mapping and return a typed document.

    This entry point is useful for programmatically generated configurations and
    avoids a JSON/YAML/TOML serialization round trip. The mapping is read but not
    modified. Missing version declarations default to APICORE 2.1.
    """
    mapping = _require_mapping(data, "$")
    target_version, declared_version = _detect_version(mapping, version)
    if target_version == "v1":
        return _build_v1(mapping)
    return _build_v2(mapping, declared_version=declared_version)


def validate(
    path: str | Path,
    *,
    version: VersionSelector | None = None,
    format: FormatName | None = None,
    encoding: str = "utf-8",
) -> Document:
    """Validate a file and return the same typed document as :func:`load`.

    This named alias is intended for validation-oriented call sites and CI code;
    successful validation returns the parsed document rather than a boolean.
    """
    return load(path, version=version, format=format, encoding=encoding)


def resolve_i18n(
    value: I18nString,
    locale: str,
    *,
    fallback_locale: str | None = None,
) -> str:
    """Resolve a localized UI value using deterministic fallback rules.

    Plain strings are returned unchanged. For language mappings the requested
    locale is preferred, followed by ``fallback_locale`` when provided, and then
    the first translation in insertion order. An empty mapping raises
    :class:`ValidationError`.
    """
    if isinstance(value, str):
        return value
    if locale in value:
        return value[locale]
    if fallback_locale is not None and fallback_locale in value:
        return value[fallback_locale]
    if value:
        return next(iter(value.values()))
    raise ValidationError("i18n value must contain at least one locale")


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


def _detect_version(
    raw: Mapping[str, Any], requested: VersionSelector | None
) -> tuple[APICoreFamily, APICoreVersion]:
    declared_raw = raw.get("APICORE_version")
    declared = (
        _normalize_declared_version(declared_raw) if declared_raw is not None else None
    )
    if requested is not None:
        forced = _normalize_requested_version(requested)
        forced_family: APICoreFamily = "v1" if forced in {"v1", "1.0"} else "v2"
        if declared is not None:
            declared_family: APICoreFamily = "v1" if declared == "1.0" else "v2"
        else:
            declared_family = forced_family
        if declared is not None and forced_family != declared_family:
            raise ValidationError(
                f"Requested version '{requested}' conflicts with APICORE_version '{declared_raw}'"
            )
        if (
            forced in {"1.0", "2.0", "2.1"}
            and declared is not None
            and forced != declared
        ):
            raise ValidationError(
                f"Requested version '{requested}' conflicts with APICORE_version '{declared_raw}'"
            )
        resolved = declared or (
            "1.0"
            if forced_family == "v1"
            else forced
            if forced in {"2.0", "2.1"}
            else "2.1"
        )
        return forced_family, resolved
    if declared is None:
        return "v2", "2.1"
    return ("v1" if declared == "1.0" else "v2"), declared


def _normalize_declared_version(value: Any) -> Literal["1.0", "2.0", "2.1"]:
    if isinstance(value, (int, float)):
        normalized = str(value)
    else:
        normalized = _require_str(value, "$.APICORE_version").strip().lower()
    normalized = normalized.replace("apicore", "").replace(" ", "")
    if normalized in {"1", "1.0", "v1"}:
        return "1.0"
    if normalized in {"2", "2.0", "v2"}:
        return "2.0"
    if normalized in {"2.1", "v2.1"}:
        return "2.1"
    raise ValidationError(f"Unsupported APICORE version: {value!r}")


def _normalize_requested_version(value: Any) -> str:
    text = _require_str(value, "version").strip().lower()
    text = text.replace("apicore", "").replace(" ", "")
    if text in {"1", "v1"}:
        return "v1"
    if text == "1.0":
        return "1.0"
    if text in {"2", "v2"}:
        return "v2"
    if text == "2.0":
        return "2.0"
    if text in {"2.1", "v2.1"}:
        return "2.1"
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
            version="1.0",
            path="$.parameters",
        ),
        response=_build_response(
            _require_mapping(raw.get("response"), "$.response"),
            "$.response",
            version="1.0",
        ),
    )
    return doc


def _build_v2(
    raw: Mapping[str, Any], *, declared_version: Literal["2.0", "2.1"]
) -> V2Document:
    if declared_version != "2.1":
        v2_1_metadata = {
            "$schema",
            "id",
            "version",
            "author",
            "license",
            "repository",
            "updated_at",
        }
        unsupported = sorted(v2_1_metadata.intersection(raw))
        if unsupported:
            raise ValidationError(
                f"APICORE v2.1 metadata requires APICORE v2.1: {unsupported}"
            )
    func = _validate_http_method(
        _require_non_empty_str(raw, "func", "$.func"), "$.func"
    )
    parameters = _build_parameters(
        _require_sequence(raw.get("parameters"), "$.parameters"),
        method=func,
        version=declared_version,
        path="$.parameters",
    )
    parameter_names = {parameter.name for parameter in parameters if parameter.name}
    if len(parameter_names) != sum(bool(parameter.name) for parameter in parameters):
        raise ValidationError("$.parameters contains duplicate parameter names")
    _validate_show_if_references(parameters, parameter_names)
    _validate_parameter_references(raw, parameter_names)
    response = _build_response(
        _require_mapping(raw.get("response"), "$.response"),
        "$.response",
        version=declared_version,
    )
    handlers = _build_handlers(
        raw.get("handlers"),
        response=response,
        path="$.handlers",
        version=declared_version,
    )
    configs = _build_configs(raw.get("configs"), "$.configs", version=declared_version)
    return V2Document(
        friendly_name=(
            _require_non_empty_i18n(raw, "friendly_name", "$.friendly_name")
            if declared_version == "2.1"
            else _require_non_empty_str(raw, "friendly_name", "$.friendly_name")
        ),
        intro=(
            _optional_i18n(raw.get("intro"), "$.intro")
            if declared_version == "2.1"
            else _optional_str(raw.get("intro"), "$.intro")
        ),
        icon=_optional_str(raw.get("icon"), "$.icon"),
        link=(
            _validate_url_template(
                _require_non_empty_str(raw, "link", "$.link"), "$.link"
            )
            if declared_version == "2.1"
            else _validate_url(_require_non_empty_str(raw, "link", "$.link"), "$.link")
        ),
        func=func,
        apicore_version=declared_version,
        parameters=parameters,
        handlers=handlers,
        configs=configs,
        response=response,
        schema_url=_optional_url(raw.get("$schema"), "$.$schema"),
        id=_optional_str(raw.get("id"), "$.id"),
        version=_optional_str(raw.get("version"), "$.version"),
        author=_optional_str(raw.get("author"), "$.author"),
        license=_optional_str(raw.get("license"), "$.license"),
        repository=_optional_url(raw.get("repository"), "$.repository"),
        updated_at=_optional_str(raw.get("updated_at"), "$.updated_at"),
        extra={
            key: value
            for key, value in raw.items()
            if key
            not in {
                "$schema",
                "id",
                "version",
                "author",
                "license",
                "repository",
                "updated_at",
                "friendly_name",
                "intro",
                "icon",
                "link",
                "func",
                "APICORE_version",
                "configs",
                "parameters",
                "handlers",
                "response",
            }
        },
    )


def _build_parameters(
    raw_items: Sequence[Any],
    *,
    method: str,
    version: Literal["1.0", "2.0", "2.1"],
    path: str,
) -> tuple[Parameter, ...]:
    return tuple(
        _build_parameter(item, method=method, version=version, path=f"{path}[{index}]")
        for index, item in enumerate(raw_items)
    )


def _build_parameter(
    raw: Any, *, method: str, version: Literal["1.0", "2.0", "2.1"], path: str
) -> Parameter:
    mapping = _require_mapping(raw, path)
    parameter_type = _require_non_empty_str(mapping, "type", f"{path}.type")
    enable = _optional_bool(mapping.get("enable"), f"{path}.enable", default=True)
    if "friendly_name" not in mapping:
        raise ValidationError(f"{path}.friendly_name is required")
    if version != "2.1" and not isinstance(mapping["friendly_name"], str):
        raise ValidationError(f"{path}.friendly_name must be a string before v2.1")
    friendly_name = _require_i18n(mapping["friendly_name"], f"{path}.friendly_name")
    if enable and not _i18n_has_text(friendly_name):
        raise ValidationError(f"{path}.friendly_name cannot be empty")
    required = _optional_bool(mapping.get("required"), f"{path}.required", default=True)
    name = _optional_str(mapping.get("name"), f"{path}.name")
    if version != "2.1":
        tooltip = _optional_str(mapping.get("tooltip"), f"{path}.tooltip")
        placeholder = _optional_str(mapping.get("placeholder"), f"{path}.placeholder")
    else:
        tooltip = _optional_i18n(mapping.get("tooltip"), f"{path}.tooltip")
        placeholder = _optional_i18n(mapping.get("placeholder"), f"{path}.placeholder")
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
        if version != "2.1":
            for index, item in enumerate(
                _require_sequence(mapping["friendly_value"], f"{path}.friendly_value")
            ):
                _require_str(item, f"{path}.friendly_value[{index}]")
        friendly_value = _i18n_tuple(
            mapping["friendly_value"], f"{path}.friendly_value"
        )
    options = None
    if "options" in mapping and mapping["options"] is not None:
        if version != "2.1":
            raise ValidationError(f"{path}.options requires APICORE v2.1")
        options = tuple(_require_sequence(mapping["options"], f"{path}.options"))
    friendly_options = None
    if "friendly_options" in mapping and mapping["friendly_options"] is not None:
        if version != "2.1":
            raise ValidationError(f"{path}.friendly_options requires APICORE v2.1")
        friendly_options = _i18n_tuple(
            mapping["friendly_options"], f"{path}.friendly_options"
        )
    if version != "2.1" and mapping.get("show_if") is not None:
        raise ValidationError(f"{path}.show_if requires APICORE v2.1")
    show_if = _build_show_if(mapping.get("show_if"), f"{path}.show_if")

    if method not in {"GET", "HEAD"} and not name:
        raise ValidationError(f"{path}.name is required when func is {method}")
    if min_value is not None and max_value is not None and min_value > max_value:
        raise ValidationError(
            f"{path}.min_value cannot be greater than {path}.max_value"
        )

    standard_types = _V1_STANDARD_TYPES if version == "1.0" else _V2_STANDARD_TYPES
    if parameter_type in standard_types:
        _validate_standard_parameter(
            parameter_type=parameter_type,
            value=value,
            friendly_value=friendly_value,
            options=options,
            friendly_options=friendly_options,
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
            "options",
            "friendly_options",
            "value",
            "tooltip",
            "placeholder",
            "text_secret",
            "friendly_name",
            "min_value",
            "max_value",
            "split_str",
            "show_if",
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
        options=options,
        friendly_options=friendly_options,
        min_value=min_value,
        max_value=max_value,
        split_str=split_str,
        tooltip=tooltip,
        placeholder=placeholder,
        text_secret=text_secret,
        show_if=show_if,
        extra=extra,
    )


def _validate_standard_parameter(
    *,
    parameter_type: str,
    value: Any,
    friendly_value: tuple[I18nString, ...] | None,
    options: tuple[Any, ...] | None,
    friendly_options: tuple[I18nString, ...] | None,
    enable: bool,
    split_str: str | None,
    min_value: float | None,
    max_value: float | None,
    placeholder: str | None,
    text_secret: bool,
    version: Literal["1.0", "2.0", "2.1"],
    path: str,
) -> None:
    if parameter_type == "integer":
        if not _is_int(value):
            raise ValidationError(f"{path}.value must be an integer")
        if version == "1.0" and (min_value is None or max_value is None):
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
        if options is not None:
            if not options:
                raise ValidationError(f"{path}.options cannot be empty")
            if _is_list_like(value):
                raise ValidationError(
                    f"{path}.value must be a single selected value when options is defined"
                )
            if not any(_same_value(value, option) for option in options):
                raise ValidationError(f"{path}.value must be present in {path}.options")
            if friendly_options is not None and len(friendly_options) != len(options):
                raise ValidationError(
                    f"{path}.friendly_options length must match {path}.options length"
                )
        else:
            if not _is_list_like(value):
                raise ValidationError(
                    f"{path}.options is required for enum parameters with a scalar value"
                )
            if not friendly_value:
                raise ValidationError(
                    f"{path}.friendly_value is required for legacy enum parameters"
                )
            if len(friendly_value) != len(value):
                raise ValidationError(
                    f"{path}.friendly_value length must match {path}.value length"
                )
        if not enable and version != "2.1":
            raise ValidationError(
                f"{path}.enable cannot be false for enum parameters before v2.1"
            )

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


def _build_response(
    raw: Mapping[str, Any], path: str, *, version: Literal["1.0", "2.0", "2.1"]
) -> ResponseConfig:
    media = None
    if "media" in raw and raw["media"] is not None:
        if version != "2.1":
            raise ValidationError(f"{path}.media requires APICORE v2.1")
        media_mapping = _require_mapping(raw["media"], f"{path}.media")
        media_type = _require_non_empty_str(media_mapping, "type", f"{path}.media.type")
        if media_type not in _MEDIA_TYPES:
            raise ValidationError(
                f"{path}.media.type must be one of {sorted(_MEDIA_TYPES)}"
            )
        content_type = _require_non_empty_str(
            media_mapping, "content_type", f"{path}.media.content_type"
        )
        if content_type not in {"URL", "BINARY"}:
            raise ValidationError(
                f"{path}.media.content_type must be 'URL' or 'BINARY'"
            )
        media_path = _require_str(media_mapping.get("path"), f"{path}.media.path")
        if content_type == "URL" and not media_path.strip():
            raise ValidationError(f"{path}.media.path cannot be empty")
        media = ResponseMedia(
            type=media_type,
            content_type=content_type,
            path=media_path,
            is_list=_optional_bool(
                media_mapping.get("is_list"), f"{path}.media.is_list", default=False
            ),
            is_base64=_optional_bool(
                media_mapping.get("is_base64"),
                f"{path}.media.is_base64",
                default=False,
            ),
        )

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
        image_path = _require_str(image_mapping.get("path"), f"{path}.image.path")
        if content_type == "URL" and not image_path.strip():
            raise ValidationError(f"{path}.image.path cannot be empty")
        image = ResponseImage(
            content_type=content_type,
            path=image_path,
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
                field_name = (
                    _require_non_empty_i18n(
                        item_mapping,
                        "friendly_name",
                        f"{path}.others[{index}].data[{data_index}].friendly_name",
                    )
                    if version == "2.1"
                    else _require_non_empty_str(
                        item_mapping,
                        "friendly_name",
                        f"{path}.others[{index}].data[{data_index}].friendly_name",
                    )
                )
                data_fields.append(
                    ResponseDataField(
                        friendly_name=field_name,
                        path=_require_non_empty_str(
                            item_mapping,
                            "path",
                            f"{path}.others[{index}].data[{data_index}].path",
                        ),
                    )
                )
            others.append(
                ResponseGroup(
                    friendly_name=(
                        _require_non_empty_i18n(
                            group_mapping,
                            "friendly_name",
                            f"{path}.others[{index}].friendly_name",
                        )
                        if version == "2.1"
                        else _require_non_empty_str(
                            group_mapping,
                            "friendly_name",
                            f"{path}.others[{index}].friendly_name",
                        )
                    ),
                    data=tuple(data_fields),
                )
            )

    if version == "2.1" and media is None and image is None:
        raise ValidationError(f"{path} must define at least one of 'media' or 'image'")
    if media is None and image is None and not others:
        raise ValidationError(
            f"{path} must define at least one of 'media', 'image', or 'others'"
        )
    return ResponseConfig(media=media, image=image, others=tuple(others))


def _build_configs(
    raw: Any, path: str, *, version: Literal["2.0", "2.1"]
) -> Configs | None:
    if raw is None:
        return None
    mapping = _require_mapping(raw, path)
    request = None
    if "request" in mapping and mapping["request"] is not None:
        request_mapping = _require_mapping(mapping["request"], f"{path}.request")
        if version != "2.1" and any(
            key in request_mapping for key in ("body_type", "body_template")
        ):
            raise ValidationError(
                f"{path}.request.body_type/body_template require APICORE v2.1"
            )
        body_type = (
            _optional_str(request_mapping.get("body_type"), f"{path}.request.body_type")
            or "json"
        )
        if body_type not in _BODY_TYPES:
            raise ValidationError(
                f"{path}.request.body_type must be one of {sorted(_BODY_TYPES)}"
            )
        body_template = request_mapping.get("body_template")
        if body_template is not None:
            if body_type == "raw" and not isinstance(body_template, str):
                raise ValidationError(
                    f"{path}.request.body_template must be a string when body_type is 'raw'"
                )
            if body_type != "raw" and not isinstance(body_template, Mapping):
                raise ValidationError(
                    f"{path}.request.body_template must be an object when body_type is '{body_type}'"
                )
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
        request = RequestConfig(
            body_type=body_type,
            body_template=body_template,
            headers=headers,
            timeout_ms=timeout_ms,
        )

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

    polling = None
    if "polling" in mapping and mapping["polling"] is not None:
        if version != "2.1":
            raise ValidationError(f"{path}.polling requires APICORE v2.1")
        polling_mapping = _require_mapping(mapping["polling"], f"{path}.polling")
        polling = PollingConfig(
            interval_ms=_require_positive_int(
                polling_mapping.get("interval_ms"), f"{path}.polling.interval_ms"
            ),
            timeout_ms=_require_positive_int(
                polling_mapping.get("timeout_ms"), f"{path}.polling.timeout_ms"
            ),
            check_link=_validate_url_template(
                _require_non_empty_str(
                    polling_mapping, "check_link", f"{path}.polling.check_link"
                ),
                f"{path}.polling.check_link",
            ),
            status_path=_require_non_empty_str(
                polling_mapping, "status_path", f"{path}.polling.status_path"
            ),
            success_value=_require_key(
                polling_mapping, "success_value", f"{path}.polling.success_value"
            ),
            failed_value=polling_mapping.get("failed_value"),
        )

    return Configs(request=request, retry=retry, rate_limit=rate_limit, polling=polling)


def _build_handlers(
    raw: Any,
    *,
    response: ResponseConfig,
    path: str,
    version: Literal["2.0", "2.1"],
) -> dict[str, HandlerRule]:
    if raw is None:
        return {}
    mapping = _require_mapping(raw, path)
    handlers: dict[str, HandlerRule] = {}
    for key, item in mapping.items():
        if isinstance(key, bool):
            raise ValidationError(
                f"{path}[key] must be an HTTP status code or 'default'"
            )
        handler_key = str(key) if _is_int(key) else _require_str(key, f"{path}[key]")
        if handler_key != "default" and (
            not handler_key.isdigit() or not 100 <= int(handler_key) <= 599
        ):
            raise ValidationError(
                f"{path}.{handler_key} must be an HTTP status code from 100 to 599 or 'default'"
            )
        handler_mapping = _require_mapping(item, f"{path}.{handler_key}")
        if handler_key in handlers:
            raise ValidationError(f"{path} contains duplicate handler '{handler_key}'")
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

        message = (
            _optional_i18n(
                handler_mapping.get("message"), f"{path}.{handler_key}.message"
            )
            if version == "2.1"
            else _optional_str(
                handler_mapping.get("message"), f"{path}.{handler_key}.message"
            )
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
        if (
            action == "response"
            and response.media is None
            and response.image is None
            and not response.others
        ):
            raise ValidationError(
                f"{path}.{handler_key} uses action 'response' but response config is empty"
            )
        if action in {"success", "warning", "error", "message"} and (
            message is None or not _i18n_has_text(message)
        ):
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


def _build_show_if(raw: Any, path: str) -> ShowIf | None:
    if raw is None:
        return None
    mapping = _require_mapping(raw, path)
    parameter = _require_non_empty_str(mapping, "parameter", f"{path}.parameter")
    has_equals = "equals" in mapping
    has_in = "in" in mapping
    if has_equals == has_in:
        raise ValidationError(f"{path} must define exactly one of 'equals' or 'in'")
    in_values = None
    if has_in:
        in_values = tuple(_require_sequence(mapping["in"], f"{path}.in"))
    return ShowIf(
        parameter=parameter,
        equals=mapping.get("equals"),
        in_values=in_values,
    )


def _validate_show_if_references(
    parameters: tuple[Parameter, ...], parameter_names: set[str]
) -> None:
    for index, parameter in enumerate(parameters):
        if parameter.show_if is None:
            continue
        target = parameter.show_if.parameter
        if target not in parameter_names:
            raise ValidationError(
                f"$.parameters[{index}].show_if references unknown parameter '{target}'"
            )
        if target == parameter.name:
            raise ValidationError(
                f"$.parameters[{index}].show_if cannot reference the same parameter"
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


def _require_key(mapping: Mapping[str, Any], key: str, path: str) -> Any:
    if key not in mapping:
        raise ValidationError(f"{path} is required")
    return mapping[key]


def _optional_str(value: Any, path: str) -> str | None:
    if value is None:
        return None
    return _require_str(value, path)


def _require_i18n(value: Any, path: str) -> I18nString:
    if isinstance(value, str):
        return value
    mapping = _require_mapping(value, path)
    if not mapping:
        raise ValidationError(f"{path} must contain at least one locale")
    result: dict[str, str] = {}
    for locale, text in mapping.items():
        locale_name = _require_str(locale, f"{path}[key]")
        if not _LOCALE_RE.fullmatch(locale_name):
            raise ValidationError(
                f"{path} locale '{locale_name}' must match 'xx' or 'xx-XX'"
            )
        result[locale_name] = _require_str(text, f"{path}.{locale_name}")
    return result


def _require_non_empty_i18n(
    mapping: Mapping[str, Any], key: str, path: str
) -> I18nString:
    if key not in mapping:
        raise ValidationError(f"{path} is required")
    value = _require_i18n(mapping[key], path)
    if not _i18n_has_text(value):
        raise ValidationError(f"{path} cannot be empty")
    return value


def _optional_i18n(value: Any, path: str) -> I18nString | None:
    if value is None:
        return None
    return _require_i18n(value, path)


def _i18n_has_text(value: I18nString) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    return any(text.strip() for text in value.values())


def _optional_url(value: Any, path: str) -> str | None:
    if value is None:
        return None
    return _validate_url(_require_str(value, path), path)


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


def _validate_url_template(value: str, path: str) -> str:
    parsed_template = urlparse(value)
    if "{{" in parsed_template.scheme or "{{" in parsed_template.netloc:
        raise ValidationError(
            f"{path} interpolation is only allowed in the URL path or query"
        )
    sanitized = re.sub(r"\{\{(?:parameters|response)\.[^{}]+\}\}", "value", value)
    if "{{" in sanitized or "}}" in sanitized:
        raise ValidationError(f"{path} contains an invalid interpolation template")
    _validate_url(sanitized, path)
    return value


def _i18n_tuple(value: Any, path: str) -> tuple[I18nString, ...]:
    items = _require_sequence(value, path)
    return tuple(
        _require_i18n(item, f"{path}[{index}]") for index, item in enumerate(items)
    )


def _same_value(left: Any, right: Any) -> bool:
    return type(left) is type(right) and left == right


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
