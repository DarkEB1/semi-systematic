"""`just new-tool`: the scaffold matches the tools contract and registers the member."""

from __future__ import annotations

import importlib.util
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("new_tool", ROOT / "scripts" / "new_tool.py")
new_tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(new_tool)

ROOT_PYPROJECT = """[project]
name = "x"
dependencies = [
    "duckdb>=1.3",
    "brain",
]

[tool.uv.workspace]
members = ["tools/*"]

[tool.uv.sources]
brain = { workspace = true }

[build-system]
requires = ["hatchling"]
"""


def test_files_follow_the_contract():
    files = new_tool.files_for("calendars", "Trading calendars.")
    assert set(files) == {
        "tools/calendars/pyproject.toml",
        "tools/calendars/src/calendars/__init__.py",
        "tools/calendars/tests/test_calendars.py",
        "tools/calendars/README.md",
    }
    meta = tomllib.loads(files["tools/calendars/pyproject.toml"])
    assert meta["project"]["name"] == "calendars"
    assert meta["tool"]["hatch"]["build"]["targets"]["wheel"]["packages"] == ["src/calendars"]
    assert "__version__" in files["tools/calendars/src/calendars/__init__.py"]
    assert "__file__" not in files["tools/calendars/src/calendars/__init__.py"]


def test_register_adds_dependency_and_source_once():
    once = new_tool.register(ROOT_PYPROJECT, "calendars")
    meta = tomllib.loads(once)
    assert "calendars" in meta["project"]["dependencies"]
    assert meta["tool"]["uv"]["sources"]["calendars"] == {"workspace": True}
    assert new_tool.register(once, "calendars") == once


def test_rejects_bad_names(capsys):
    assert new_tool.main(["Bad-Name", "--dry-run"]) == 2
