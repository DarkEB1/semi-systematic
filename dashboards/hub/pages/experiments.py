"""Experiments page: research/experiments/*/config.yaml + results.md, filterable by owner, tag,
dataset and status."""

from __future__ import annotations

import yaml

from pages import ROOT, frontmatter

EXPERIMENTS = ROOT / "research" / "experiments"


def rows() -> list[dict]:
    out = []
    for folder in sorted(EXPERIMENTS.glob("*/"), reverse=True):
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
    data = filtered(filters)
    if not data:
        return mo.md("_No experiments match. `just experiment <slug>` creates one._")
    return mo.vstack(
        [mo.md(f"**{len(data)} experiment(s)** (newest first)"), mo.ui.table(data, selection=None)]
    )
