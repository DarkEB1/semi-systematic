"""Experiments page: projects (research/<project>/README.md) and their experiments
(research/<project>/experiments/*/config.yaml + results.md), filterable by owner, tag, dataset
and status."""

from __future__ import annotations

import yaml

from pages import ROOT, frontmatter

RESEARCH = ROOT / "research"


def projects() -> list[dict]:
    out = []
    for folder in sorted(p for p in RESEARCH.iterdir() if (p / "README.md").exists()):
        fm = frontmatter(folder / "README.md")
        n = len([p for p in (folder / "experiments").glob("*/") if (p / "config.yaml").exists()])
        out.append(
            {
                "project": folder.name,
                "title": str(fm.get("title", folder.name)),
                "owner": str(fm.get("owner", "")),
                "status": str(fm.get("status", "")),
                "tags": ", ".join(map(str, fm.get("tags") or [])),
                "experiments": n,
                "readme": f"research/{folder.name}/README.md",
            }
        )
    return out


def rows() -> list[dict]:
    out = []
    for folder in sorted(RESEARCH.glob("*/experiments/*/"), key=lambda p: p.name, reverse=True):
        cfg_path = folder / "config.yaml"
        if not cfg_path.exists():
            continue
        try:
            cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            cfg = {}
        res = frontmatter(folder / "results.md") if (folder / "results.md").exists() else {}
        out.append(
            {
                "project": str(cfg.get("project", folder.parent.parent.name)),
                "folder": folder.name,
                "slug": str(cfg.get("slug", folder.name)),
                "date": str(cfg.get("date", folder.name[:10])),
                "owner": str(cfg.get("owner", res.get("owner", ""))),
                "status": str(res.get("status", "")),
                "tags": ", ".join(map(str, cfg.get("tags") or [])),
                "datasets": ", ".join(
                    f"{d.get('name')}@{d.get('snapshot')}"
                    for d in (cfg.get("datasets") or [])
                    if isinstance(d, dict)
                ),
                "parent": str(cfg.get("parent", "")),
                "hypothesis": str(cfg.get("hypothesis", ""))[:120],
            }
        )
    return out


def filtered(filters: dict) -> list[dict]:
    out = rows()
    if filters.get("owner"):
        out = [r for r in out if filters["owner"].lower() in r["owner"].lower()]
    if filters.get("tag"):
        out = [r for r in out if filters["tag"].lower() in r["tags"].lower()]
    if filters.get("dataset"):
        out = [r for r in out if filters["dataset"].lower() in r["datasets"].lower()]
    if filters.get("status"):
        out = [r for r in out if r["status"] == filters["status"]]
    return out


def render(mo, filters: dict):
    parts = []
    projs = projects()
    parts.append(
        mo.md(
            f"**{len(projs)} project(s)**. A project is a folder under `research/`; `just project <slug>` creates one."
        )
    )
    if projs:
        parts.append(mo.ui.table(projs, selection=None))
    data = filtered(filters)
    if not data:
        parts.append(
            mo.md("_No experiments match. `just experiment <slug> --project <p>` creates one._")
        )
    else:
        parts.append(mo.md(f"**{len(data)} experiment(s)** (newest first)"))
        parts.append(mo.ui.table(data, selection=None))
    return mo.vstack(parts)
