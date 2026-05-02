from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version as _package_version

from apicore.errors import APICoreError, ParseError, ValidationError
from apicore.models import APICoreVersion, Document, FormatName, V1Document, V2Document
from apicore.parser import load, loads, validate

try:
    __version__ = _package_version("APICORE_Python")
except PackageNotFoundError:
    __version__ = "0.0.0"

__all__ = [
    "APICoreError",
    "APICoreVersion",
    "Document",
    "FormatName",
    "ParseError",
    "ValidationError",
    "V1Document",
    "V2Document",
    "__version__",
    "load",
    "loads",
    "validate",
]
