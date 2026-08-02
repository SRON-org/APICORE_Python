from __future__ import annotations

from pathlib import Path
from typing import get_args

import apicore


def test_documented_public_api_is_exported() -> None:
    expected = {
        "APICoreError",
        "APICoreFamily",
        "APICoreSpecVersion",
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
        "load",
        "loads",
        "parse",
        "resolve_i18n",
        "validate",
    }

    assert expected <= set(apicore.__all__)
    for name in expected:
        assert getattr(apicore, name) is not None


def test_apicore_version_retains_v2_0_public_alias_semantics() -> None:
    assert get_args(apicore.APICoreVersion) == ("v1", "v2")


def test_tool_modules_are_not_part_of_source_package() -> None:
    package_dir = Path(apicore.__path__[0])
    assert not (package_dir / "cli.py").exists()
    assert not (package_dir / "gui.py").exists()
