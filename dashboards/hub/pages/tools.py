"""Tools page: every isolated package under tools/, with version, description and public API."""

from __future__ import annotations

import ast
import tomllib

from pages import ROOT

TOOLS = ROOT / "tools"


def _public_api(init: object) -> str:
    try:
        tree = ast.parse(init.read_text(encoding="utf-8"))  # type: ignore[attr-defined]
    except (SyntaxError, OSError):
        return ""
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "__all__" for t in node.targets
        ):
            try:
                return ", ".join(map(str, ast.literal_eval(node.value)))
            except ValueError:
                return ""
    return ""


def rows() -> list[dict]:
    out = []
    for folder in sorted(
        p for p in TOOLS.iterdir() if p.is_dir() and not p.name.startswith((".", "_"))
    ):
        pyproject = folder / "pyproject.toml"
        if not pyproject.exists():
            continue
        meta = tomllib.loads(pyproject.read_text(encoding="utf-8")).get("project", {})
        out.append(
            {
                "tool": folder.name,
                "version": str(meta.get("version", "")),
                "description": str(meta.get("description", "")),
                "depends on": ", ".join(meta.get("dependencies", [])),
                "public api": _public_api(folder / "src" / folder.name / "__init__.py"),
                "readme": f"tools/{folder.name}/README.md",
            }
        )
    return out


def render(mo, filters: dict):
    data = rows()
    if not data:
        return mo.md(
            "_No tools yet. `just new-tool NAME` creates one (contract in tools/README.md)._"
        )
    return mo.vstack(
        [
            mo.md(
                f"**{len(data)} tool(s)**. Isolated packages; code moves here from an experiment on second use, with a test, in its own PR."
            ),
            mo.ui.table(data, selection=None),
        ]
    )
