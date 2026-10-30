#!/usr/bin/env python
"""Tools are isolated packages. Fail when one breaks the contract in tools/README.md.

Per tool under tools/<name>/:
- pyproject.toml with project.name == <name>, src/<name>/__init__.py, README.md, tests/ with a test
- the package imports only its declared dependencies: never quant, scripts, dashboards or another
  tool unless that tool is listed under [project.dependencies]
- the package never locates the repository from its own file (no ``__file__``); paths are arguments
- the root pyproject lists the tool as a dependency and as a workspace source

Repo-wide: no ``sys.path.insert`` outside the three allow-listed script-tier files; installed
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
REPO_PACKAGES = {"quant", "scripts", "dashboards", "pages", "tests"}
SYS_PATH_ALLOW = {
    "dashboards/hub/app.py",  # marimo runs app.py as a file; its pages/ package is next to it
    "scripts/tags.py",  # scripts/ is not a package; sibling import
    ".claude/skills/repo-structure/run.py",  # imports scripts/check_frontmatter.py constants
}
SCAN_DIRS = ("src", "scripts", "tools", "dashboards", ".claude", "tests", "research")


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
    return names


def _dep_names(deps: list[str]) -> set[str]:
    return {re.split(r"[\s<>=!~\[;]", d, maxsplit=1)[0].lower() for d in deps}


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
    for py in sorted(pkg.rglob("*.py")) if pkg.exists() else []:
        rel = py.relative_to(ROOT).as_posix()
        for mod in sorted(_imports(py)):
            if mod in REPO_PACKAGES:
                errs.append(f"{rel}: imports {mod!r}; a tool never imports the repo's own code")
            elif mod in all_tools and mod != name and mod not in declared:
                errs.append(
                    f"{rel}: imports tool {mod!r} without declaring it in tools/{name}/pyproject.toml"
                )
        if "__file__" in py.read_text(encoding="utf-8"):
            errs.append(f"{rel}: uses __file__; a tool takes paths as arguments (see brain.Repo)")
    return errs


def check_sys_path() -> list[str]:
    errs = []
    for d in SCAN_DIRS:
        base = ROOT / d
        if not base.exists():
            continue
        for py in base.rglob("*.py"):
            if "__pycache__" in py.parts or ".venv" in py.parts:
                continue
            rel = py.relative_to(ROOT).as_posix()
            if rel in SYS_PATH_ALLOW or py.resolve() == Path(__file__).resolve():
                continue
            if "sys.path.insert" in py.read_text(encoding="utf-8", errors="replace"):
                errs.append(f"{rel}: sys.path.insert; import the installed package instead")
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
    errs += check_sys_path()
    for e in errs:
        print(e)
    print(f"tools: {len(tools)} tool(s) checked, {len(errs)} problem(s)")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
