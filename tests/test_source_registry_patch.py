"""Source scaffolding must survive Ruff's grouped import formatting."""

import runpy
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    "imports",
    [
        "from quant.ingest import yahoo, nyfed\n",
        "from quant.ingest import (\n    yahoo,\n    nyfed,\n)\n",
    ],
)
def test_grouped_import_and_idempotence(tmp_path, imports):
    namespace = runpy.run_path(str(ROOT / ".claude/skills/pull-data/pull_data.py"))
    patch = namespace["registry_patch"]
    registry = tmp_path / "registry.py"
    registry.write_text(
        imports + "SOURCES: dict[str, ModuleType] = {\n    yahoo.SOURCE: yahoo,\n}\n"
    )
    patch.__globals__["REGISTRY"] = registry
    _, updated = patch("newsrc")
    assert "from quant.ingest import newsrc\n" in updated
    assert "newsrc.SOURCE: newsrc," in updated
    compile(updated, str(registry), "exec")
    registry.write_text(updated)
    assert patch("newsrc") == (updated, updated)
