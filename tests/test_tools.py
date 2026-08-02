from __future__ import annotations

import runpy
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "tools" / "cli.py"
GUI = ROOT / "tools" / "gui.py"


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_repository_cli_help() -> None:
    result = _run_cli("--help")
    assert result.returncode == 0
    assert "Validate APICORE configuration files" in result.stdout


def test_repository_cli_validates_file(tmp_path: Path) -> None:
    path = tmp_path / "valid.api.json"
    path.write_text(
        '{"friendly_name":"Demo","link":"https://api.example.com/x",'
        '"func":"GET","parameters":[],"response":{'
        '"media":{"type":"text","content_type":"BINARY","path":"data.text"}}}',
        encoding="utf-8",
    )

    result = _run_cli(str(path))
    assert result.returncode == 0
    assert "Valid APICORE 2.1 file" in result.stdout


def test_repository_cli_handles_missing_file_without_traceback(tmp_path: Path) -> None:
    result = _run_cli(str(tmp_path / "missing.api.json"))
    assert result.returncode == 1
    assert "Validation failed:" in result.stderr
    assert "Traceback" not in result.stderr


def test_repository_gui_script_can_be_loaded_without_starting_window() -> None:
    pytest.importorskip("tkinter")
    namespace = runpy.run_path(str(GUI), run_name="gui_smoke")
    assert "APICoreValidatorGUI" in namespace
    assert callable(namespace["main"])
