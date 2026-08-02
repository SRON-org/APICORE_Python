from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _package_version

from apicore.errors import APICoreError, ParseError, ValidationError
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
from apicore.parser import load, loads, parse, resolve_i18n, validate

try:
    __version__ = _package_version("APICORE_Python")
except PackageNotFoundError:
    __version__ = "0.0.0"

__all__ = [
    "APICoreError",
    "APICoreFamily",
    "APICoreVersion",
    "Configs",
    "Document",
    "FormatName",
    "HandlerRule",
    "I18nString",
    "Parameter",
    "ParseError",
    "PollingConfig",
    "RateLimit",
    "RequestConfig",
    "ResponseConfig",
    "ResponseDataField",
    "ResponseGroup",
    "ResponseImage",
    "ResponseMedia",
    "RetryPolicy",
    "ShowIf",
    "V1Document",
    "V2Document",
    "ValidationError",
    "VersionSelector",
    "__version__",
    "load",
    "loads",
    "parse",
    "resolve_i18n",
    "validate",
]
