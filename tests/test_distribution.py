from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_package_source_contains_only_library_modules() -> None:
    package_files = {path.name for path in (ROOT / "src" / "apicore").glob("*.py")}
    assert package_files == {"__init__.py", "errors.py", "models.py", "parser.py"}


def test_project_defines_no_installed_tool_entry_points() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "[project.scripts]" not in pyproject
    assert "apicore-validate" not in pyproject
    assert "apicore-gui" not in pyproject


def test_repository_tools_remain_available() -> None:
    assert (ROOT / "tools" / "cli.py").is_file()
    assert (ROOT / "tools" / "gui.py").is_file()
