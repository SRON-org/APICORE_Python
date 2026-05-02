from __future__ import annotations


class APICoreError(Exception):
    """Base exception for the library."""


class ParseError(APICoreError):
    """Raised when the input document cannot be decoded."""


class ValidationError(APICoreError):
    """Raised when the decoded document violates the APICORE schema."""
