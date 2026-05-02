from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, TypeAlias

APICoreVersion: TypeAlias = Literal["v1", "v2"]
FormatName: TypeAlias = Literal["json", "yaml", "toml"]


@dataclass(slots=True, frozen=True)
class Parameter:
    enable: bool
    name: str | None
    type: str
    required: bool
    value: Any
    friendly_name: str
    friendly_value: tuple[str, ...] | None = None
    min_value: int | float | None = None
    max_value: int | float | None = None
    split_str: str | None = None
    tooltip: str | None = None
    placeholder: str | None = None
    text_secret: bool = False
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class ResponseImage:
    content_type: Literal["URL", "BINARY"]
    path: str
    is_list: bool = False
    is_base64: bool = False


@dataclass(slots=True, frozen=True)
class ResponseDataField:
    friendly_name: str
    path: str


@dataclass(slots=True, frozen=True)
class ResponseGroup:
    friendly_name: str
    data: tuple[ResponseDataField, ...]


@dataclass(slots=True, frozen=True)
class ResponseConfig:
    image: ResponseImage | None = None
    others: tuple[ResponseGroup, ...] = ()


@dataclass(slots=True, frozen=True)
class RequestConfig:
    headers: dict[str, str] = field(default_factory=dict)
    timeout_ms: int | str = 30000


@dataclass(slots=True, frozen=True)
class RetryPolicy:
    count: int = 3
    delay_ms: int = 10_000


@dataclass(slots=True, frozen=True)
class RateLimit:
    frequency: int | None = None
    per: Literal["sec", "min", "hour", "day"] = "min"


@dataclass(slots=True, frozen=True)
class Configs:
    request: RequestConfig | None = None
    retry: RetryPolicy | None = None
    rate_limit: RateLimit | None = None


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
    message: str | None = None
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
    friendly_name: str
    link: str
    func: str
    apicore_version: Literal["2.0"] = "2.0"
    parameters: tuple[Parameter, ...] = ()
    response: ResponseConfig = field(default_factory=ResponseConfig)
    intro: str | None = None
    icon: str | None = None
    configs: Configs | None = None
    handlers: dict[str, HandlerRule] = field(default_factory=dict)


Document: TypeAlias = V1Document | V2Document
