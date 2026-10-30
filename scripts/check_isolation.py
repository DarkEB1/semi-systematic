#!/usr/bin/env python
"""Everything is isolated; it comes together only in the data layer, the dashboard and knowledge/.

Units and what each may import (ADR-0003):

| unit | may import | never |
|---|---|---|
| tools/<name>/src | its declared dependencies (other tools only if declared) | quant, scripts, dashboards, research, tests |
| research/<project>/experiments/<x> | quant (the data layer), tools, third-party | another experiment, research, dashboards, scripts, tests |
| src/quant | third-party, tools | research, dashboards, scripts, tests |
| scripts, .claude/skills | quant, tools, third-party | research, dashboards |
| dashboards/hub | anything (it is where things come together) | imported by nothing |

Per tool it also checks the package contract from tools/README.md: pyproject with the folder's
name, src/<name>/__init__.py, README.md, tests/test_*.py, listed in the root pyproject as a
dependency and a workspace source, and no ``__file__`` (paths are arguments).

Repo-wide: no ``sys.path.insert`` outside three allow-listed script-tier files; installed
packages are imported, not path-hacked.
"""

from __future__ import annotations

import ast
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
RESEARCH = ROOT / "research"
REPO_UNITS = {"quant", "scripts", "dashboards", "pages", "tests", "research"}
SYS_PATH_ALLOW = {
    "dashboards/hub/app.py",  # marimo runs app.py as a file; its pages/ package is next to it
    "scripts/tags.py",  # scripts/ is not a package; sibling import
    ".claude/skills/repo-structure/run.py",  # imports scripts/check_frontmatter.py constants
}
SCAN_DIRS = ("src", "scripts", "tools", "dashboards", ".claude", "tests", "research")


def _py_files(base: Path) -> list[Path]:
    if not base.exists():
        return []
    return sorted(
        p
        for p in base.rglob("*.py")
        if "__pycache__" not in p.parts and ".venv" not in p.parts and "outputs" not in p.parts
    )


def _imports(py: Path) -> set[str]:
    try:
        tree = ast.parse(py.read_text(encoding="utf-8"))
    except SyntaxError:
        return set()
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.level > 0:
            names.add(".")  # relative import
    return names


def _dep_names(deps: list[str]) -> set[str]:
    return {re.split(r"[\s<>=!~\[;]", d, maxsplit=1)[0].lower() for d in deps}


def _rel(p: Path) -> str:
    return p.relative_to(ROOT).as_posix()


def _forbid(files: list[Path], forbidden: set[str], unit: str) -> list[str]:
    errs = []
    for py in files:
        for mod in sorted(_imports(py) & forbidden):
            errs.append(
                f"{_rel(py)}: {unit} imports {mod!r}; isolated units meet only in the data layer, the dashboard and knowledge/"
            )
    return errs


# --------------------------------------------------------------------------- tools


def check_tool(
    tool: Path, all_tools: set[str], root_deps: set[str], root_sources: set[str]
) -> list[str]:
    name = tool.name
    errs: list[str] = []
    pyproject = tool / "pyproject.toml"
    if not pyproject.exists():
        return [f"tools/{name}: missing pyproject.toml"]
    meta = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    project = meta.get("project", {})
    if project.get("name") != name:
        errs.append(f"tools/{name}: project.name is {project.get('name')!r}, must be {name!r}")
    pkg = tool / "src" / name
    if not (pkg / "__init__.py").exists():
        errs.append(f"tools/{name}: missing src/{name}/__init__.py (src layout)")
    if not (tool / "README.md").exists():
        errs.append(f"tools/{name}: missing README.md")
    if not list((tool / "tests").glob("test_*.py")):
        errs.append(f"tools/{name}: tests/ has no test_*.py")
    if name not in root_deps:
        errs.append(f"tools/{name}: not listed under [project.dependencies] in the root pyproject")
    if name not in root_sources:
        errs.append(f"tools/{name}: not listed under [tool.uv.sources] as a workspace member")
    declared = _dep_names(project.get("dependencies", []))
    files = _py_files(pkg)
    errs += _forbid(files, REPO_UNITS, f"tool {name}")
    for py in files:
        for mod in sorted(_imports(py)):
            if mod in all_tools and mod != name and mod not in declared:
                errs.append(
                    f"{_rel(py)}: imports tool {mod!r} without declaring it in tools/{name}/pyproject.toml"
                )
        if "__file__" in py.read_text(encoding="utf-8"):
            errs.append(
                f"{_rel(py)}: uses __file__; a tool takes paths as arguments (see brain.Repo)"
            )
    return errs


# --------------------------------------------------------------------------- other units


def check_experiments() -> list[str]:
    errs: list[str] = []
    for folder in sorted(p for p in RESEARCH.glob("*/experiments/*/") if p.is_dir()):
        files = _py_files(folder)
        errs += _forbid(files, REPO_UNITS - {"quant"} | {"."}, f"experiment {folder.name}")
    return errs


def check_data_layer() -> list[str]:
    return _forbid(
        _py_files(ROOT / "src" / "quant"),
        {"research", "dashboards", "pages", "scripts", "tests"},
        "src/quant",
    )


def check_scripts_and_skills() -> list[str]:
    files = _py_files(ROOT / "scripts") + _py_files(ROOT / ".claude" / "skills")
    return _forbid(files, {"research", "dashboards", "pages"}, "script")


def check_sys_path() -> list[str]:
    errs = []
    me = Path(__file__).resolve()
    for d in SCAN_DIRS:
        for py in _py_files(ROOT / d):
            if _rel(py) in SYS_PATH_ALLOW or py.resolve() == me:
                continue
            if "sys.path.insert" in py.read_text(encoding="utf-8", errors="replace"):
                errs.append(f"{_rel(py)}: sys.path.insert; import the installed package instead")
    return errs


def main() -> int:
    root_meta = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    root_deps = _dep_names(root_meta.get("project", {}).get("dependencies", []))
    root_sources = {
        k
        for k, v in root_meta.get("tool", {}).get("uv", {}).get("sources", {}).items()
        if isinstance(v, dict) and v.get("workspace")
    }
    tools = sorted(p for p in TOOLS.iterdir() if p.is_dir() and not p.name.startswith((".", "_")))
    names = {t.name for t in tools}
    errs: list[str] = []
    for t in tools:
        errs += check_tool(t, names, root_deps, root_sources)
    errs += check_experiments()
    errs += check_data_layer()
    errs += check_scripts_and_skills()
    errs += check_sys_path()
    for e in errs:
        print(e)
    n_exp = len(list(RESEARCH.glob("*/experiments/*/")))
    print(f"isolation: {len(tools)} tool(s), {n_exp} experiment(s) checked, {len(errs)} problem(s)")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
