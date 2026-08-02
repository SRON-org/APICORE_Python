from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, TypeAlias

APICoreVersion: TypeAlias = Literal["v1", "v2"]  # noqa: UP040
type APICoreSpecVersion = Literal["1.0", "2.0", "2.1"]
type APICoreFamily = Literal["v1", "v2"]
type VersionSelector = Literal["v1", "1.0", "v2", "2.0", "2.1", "v2.1"]
type FormatName = Literal["json", "yaml", "toml"]
type I18nString = str | dict[str, str]


@dataclass(slots=True, frozen=True)
class Parameter:
    enable: bool
    name: str | None
    type: str
    required: bool
    value: Any
    friendly_name: I18nString
    friendly_value: tuple[I18nString, ...] | None = None
    min_value: int | float | None = None
    max_value: int | float | None = None
    split_str: str | None = None
    tooltip: I18nString | None = None
    placeholder: I18nString | None = None
    text_secret: bool = False
    extra: dict[str, Any] = field(default_factory=dict)
    options: tuple[Any, ...] | None = None
    friendly_options: tuple[I18nString, ...] | None = None
    show_if: ShowIf | None = None


@dataclass(slots=True, frozen=True)
class ShowIf:
    parameter: str
    equals: Any = None
    in_values: tuple[Any, ...] | None = None


@dataclass(slots=True, frozen=True)
class ResponseImage:
    content_type: Literal["URL", "BINARY"]
    path: str
    is_list: bool = False
    is_base64: bool = False


@dataclass(slots=True, frozen=True)
class ResponseMedia:
    type: Literal["image", "audio", "video", "text", "markdown", "file"]
    content_type: Literal["URL", "BINARY"]
    path: str
    is_list: bool = False
    is_base64: bool = False


@dataclass(slots=True, frozen=True)
class ResponseDataField:
    friendly_name: I18nString
    path: str


@dataclass(slots=True, frozen=True)
class ResponseGroup:
    friendly_name: I18nString
    data: tuple[ResponseDataField, ...]


@dataclass(slots=True, frozen=True)
class ResponseConfig:
    image: ResponseImage | None = None
    others: tuple[ResponseGroup, ...] = ()
    media: ResponseMedia | None = None

    @property
    def preferred_media(self) -> ResponseMedia | None:
        if self.media is not None:
            return self.media
        if self.image is None:
            return None
        return ResponseMedia(
            type="image",
            content_type=self.image.content_type,
            path=self.image.path,
            is_list=self.image.is_list,
            is_base64=self.image.is_base64,
        )


@dataclass(slots=True, frozen=True)
class RequestConfig:
    headers: dict[str, str] = field(default_factory=dict)
    timeout_ms: int | str = 30000
    body_type: Literal["json", "form-data", "x-www-form-urlencoded", "raw"] = "json"
    body_template: Any = None


@dataclass(slots=True, frozen=True)
class RetryPolicy:
    count: int = 3
    delay_ms: int = 10_000


@dataclass(slots=True, frozen=True)
class RateLimit:
    frequency: int | None = None
    per: Literal["sec", "min", "hour", "day"] = "min"


@dataclass(slots=True, frozen=True)
class PollingConfig:
    interval_ms: int
    timeout_ms: int
    check_link: str
    status_path: str
    success_value: Any
    failed_value: Any = None


@dataclass(slots=True, frozen=True)
class Configs:
    request: RequestConfig | None = None
    retry: RetryPolicy | None = None
    rate_limit: RateLimit | None = None
    polling: PollingConfig | None = None


@dataclass(slots=True, frozen=True)
class HandlerRule:
    action: Literal[
        "response",
        "success",
        "warning",
        "error",
        "message",
        "browser",
        "run",
        "retry",
        "return",
    ]
    extract: dict[str, str] = field(default_factory=dict)
    message: I18nString | None = None
    link: str | None = None
    script: str | None = None
    front: bool = False
    count: int | None = None
    delay_ms: int | None = None


@dataclass(slots=True, frozen=True)
class V1Document:
    friendly_name: str
    link: str
    func: str
    apicore_version: Literal["1.0"] = "1.0"
    parameters: tuple[Parameter, ...] = ()
    response: ResponseConfig = field(default_factory=ResponseConfig)
    intro: str | None = None
    icon: str | None = None


@dataclass(slots=True, frozen=True)
class V2Document:
    friendly_name: I18nString
    link: str
    func: str
    apicore_version: Literal["2.0", "2.1"] = "2.0"
    parameters: tuple[Parameter, ...] = ()
    response: ResponseConfig = field(default_factory=ResponseConfig)
    intro: I18nString | None = None
    icon: str | None = None
    configs: Configs | None = None
    handlers: dict[str, HandlerRule] = field(default_factory=dict)
    schema_url: str | None = None
    id: str | None = None
    version: str | None = None
    author: str | None = None
    license: str | None = None
    repository: str | None = None
    updated_at: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


type Document = V1Document | V2Document
