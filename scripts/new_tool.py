#!/usr/bin/env python
"""`just new-tool NAME`: scaffold tools/<name>/ as an isolated workspace package.

Writes pyproject.toml, src/<name>/__init__.py, tests/test_<name>.py and README.md, then registers
the tool in the root pyproject ([project.dependencies] and [tool.uv.sources]). Finish with
`uv lock && just setup` so the lockfile and the venv know the new member. The contract every tool
follows is tools/README.md; `just check` enforces it (scripts/check_tools.py).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"

PYPROJECT = """[project]
name = "{name}"
version = "0.1.0"
description = "{description}"
requires-python = ">=3.12,<3.13"
dependencies = []

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/{name}"]
"""

INIT = '''"""{name}: {description}

A tool: an isolated package that takes its inputs as arguments and knows nothing about the
repository around it. Contract: tools/README.md.
"""

from __future__ import annotations

__version__ = "0.1.0"
__all__: list[str] = []
'''

TEST = '''"""{name}: tests run without the repository, the bucket or .env."""

from __future__ import annotations

import {name}


def test_import() -> None:
    assert {name}.__version__
'''

README = """# {name}

{description}

Status: new. A tool is an isolated package (contract in [tools/README.md](../README.md)): it
imports only what its own `pyproject.toml` declares, takes every path and setting as an argument,
and its tests run without the repository, the bucket or `.env`.

## Use

```python
import {name}
```

## Develop

- Code in `src/{name}/`, public API in `__all__`.
- Tests in `tests/`, run by `just test`.
- Dependencies in this folder's `pyproject.toml`; one lockfile at the repo root (`uv lock`).
"""


def files_for(name: str, description: str) -> dict[str, str]:
    base = f"tools/{name}"
    ctx = {"name": name, "description": description}
    return {
        f"{base}/pyproject.toml": PYPROJECT.format(**ctx),
        f"{base}/src/{name}/__init__.py": INIT.format(**ctx),
        f"{base}/tests/test_{name}.py": TEST.format(**ctx),
        f"{base}/README.md": README.format(**ctx),
    }


def register(pyproject_text: str, name: str) -> str:
    """Add the tool to [project.dependencies] and [tool.uv.sources] of the root pyproject."""
    if re.search(rf'^\s*"{re.escape(name)}",\s*$', pyproject_text, flags=re.M):
        return pyproject_text
    text = re.sub(
        r"(\[project\][\s\S]*?dependencies = \[[\s\S]*?)(\n\])",
        lambda m: f'{m.group(1)}\n    "{name}",{m.group(2)}',
        pyproject_text,
        count=1,
    )
    text = re.sub(
        r"(\[tool\.uv\.sources\]\n(?:.*\n)*?)(?=\n\[|\Z)",
        lambda m: m.group(1) + f"{name} = {{ workspace = true }}\n",
        text,
        count=1,
    )
    return text


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="just new-tool")
    p.add_argument("name", help="lowercase identifier; becomes the import name")
    p.add_argument("--description", default="TODO: one line on what this tool does.")
    p.add_argument("--dry-run", action="store_true", help="print files instead of writing")
    a = p.parse_args(argv)
    if not re.fullmatch(r"[a-z][a-z0-9_]{1,30}", a.name):
        print("name must be a lowercase python identifier", file=sys.stderr)
        return 2
    if (TOOLS / a.name).exists() and not a.dry_run:
        print(f"tools/{a.name} exists", file=sys.stderr)
        return 1
    files = files_for(a.name, a.description)
    root_py = ROOT / "pyproject.toml"
    new_root = register(root_py.read_text(encoding="utf-8"), a.name)
    if a.dry_run:
        for rel, text in files.items():
            print(f"--- {rel}")
            print(text, end="")
        print("--- patch pyproject.toml")
        print(
            f'    "{a.name}",  under [project.dependencies]; {a.name} = {{ workspace = true }} under [tool.uv.sources]'
        )
        return 0
    for rel, text in files.items():
        path = ROOT / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        print(rel)
    root_py.write_text(new_root, encoding="utf-8")
    print("pyproject.toml (registered)")
    print(f"next: uv lock && just setup, then write tools/{a.name}/README.md and `just check`")
    return 0


if __name__ == "__main__":
    sys.exit(main())
