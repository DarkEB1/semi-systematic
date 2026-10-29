#!/usr/bin/env python
"""Deterministic part of the new-experiment skill (`just experiment SLUG`).

create:  research/experiments/<date>-<slug>/{config.yaml, run.py, results.md, figures/}
finish:  `--finish` drafts results.md and knowledge/research-log/<date>-<slug>.md from
         config.yaml and the files under outputs/; it never invents a number that is not in outputs/.
dupes:   `--check-dupes` (also run by --finish) flags functions whose source is identical to one in
         another experiment's run.py: the reuse rule says move it to research/signals or src/quant
         on second use, with a test, in its own PR.
"""

from __future__ import annotations

import argparse
import ast
import datetime as dt
import hashlib
import json
import os
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
EXPERIMENTS = ROOT / "research" / "experiments"
RESEARCH_LOG = ROOT / "knowledge" / "research-log"
TEAM = ROOT / "knowledge" / "context" / "team.yaml"

NOTEBOOK = """import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium")


@app.cell
def _():
    import json
    import pathlib

    import marimo as mo
    import yaml

    from quant import data

    HERE = pathlib.Path(__file__).resolve().parent
    config = yaml.safe_load((HERE / "config.yaml").read_text(encoding="utf-8"))
    mo.md(f"# {config['slug']}\\n\\n{config.get('hypothesis', '')}")
    return HERE, config, data, json, mo


@app.cell
def _(config, data):
    # Only the datasets named in config.yaml, at the snapshots named there.
    tables = data.load(config)
    tables
    return (tables,)


@app.cell
def _(HERE, config, json, tables):
    # Everything --finish may quote must be written to outputs/. No other numbers count.
    out = HERE / "outputs"
    out.mkdir(exist_ok=True)
    metrics = {
        "seed": config.get("seed"),
        "datasets_loaded": len(tables),
        "rows": {k: v.num_rows for k, v in tables.items()},
    }
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    metrics
    return


if __name__ == "__main__":
    app.run()
"""


def default_owner() -> str:
    if os.getenv("R2_HANDLE"):
        return os.environ["R2_HANDLE"]
    team = yaml.safe_load(TEAM.read_text(encoding="utf-8")) if TEAM.exists() else {}
    return str(
        (team or {}).get("data_layer_owner") or ((team or {}).get("handles") or ["unknown"])[0]
    )


def config_text(
    slug: str,
    owner: str,
    date: str,
    hypothesis: str,
    datasets: list[str],
    parent: str | None,
    seed: int,
) -> str:
    ds = []
    for d in datasets:
        name, _, snap = d.partition(":")
        ds.append({"name": name, "snapshot": snap or "YYYY-MM-DD"})
    cfg = {
        "slug": slug,
        "date": date,
        "owner": owner,
        "hypothesis": hypothesis,
        **({"parent": parent} if parent else {}),
        "datasets": ds,
        "params": {"cost_bp": 5, "lookback_days": 20},
        "seed": seed,
    }
    return yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True)


def results_text(slug: str, owner: str, date: str, hypothesis: str) -> str:
    return f"""---
slug: {slug}
status: draft
date: {date}
owner: {owner}
---

# {slug}

Status: draft. Set `status: final` in the frontmatter when done; the folder is frozen from then on
(`just check` refuses later edits) and a follow-up is a new experiment with `parent: {slug}`.

## Hypothesis

{hypothesis}

## Result

_Drafted by `just experiment {slug} --finish` from outputs/; nothing here is typed by hand._

## Figures

_PNG files under figures/, each under 1 MB._
"""


def files_for(
    slug: str,
    owner: str,
    date: str,
    hypothesis: str,
    datasets: list[str],
    parent: str | None,
    seed: int,
) -> dict[str, str]:
    folder = f"research/experiments/{date}-{slug}"
    return {
        f"{folder}/config.yaml": config_text(slug, owner, date, hypothesis, datasets, parent, seed),
        f"{folder}/run.py": NOTEBOOK,
        f"{folder}/results.md": results_text(slug, owner, date, hypothesis),
        f"{folder}/figures/.gitkeep": "",
    }


def emit(files: dict[str, str], dry_run: bool) -> None:
    for rel, text in files.items():
        if dry_run:
            print(f"--- {rel}")
            print(text, end="" if text.endswith("\n") or not text else "\n")
            continue
        p = ROOT / rel
        if p.exists() and p.name != ".gitkeep":
            print(f"exists, not overwritten: {rel}", file=sys.stderr)
            continue
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        print(rel)


# --------------------------------------------------------------------------- duplicates


def _function_hashes(path: Path) -> dict[str, str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, OSError):
        return {}
    out = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and not node.name.startswith(
            "_"
        ):
            src = ast.unparse(node)
            if len(src.splitlines()) < 4:
                continue
            out[node.name] = hashlib.sha1(src.encode()).hexdigest()[:12]
    return out


def check_dupes(folder: Path) -> list[str]:
    mine = {}
    for py in folder.rglob("*.py"):
        mine.update({f"{py.name}:{k}": v for k, v in _function_hashes(py).items()})
    warnings = []
    for other in sorted(EXPERIMENTS.glob("*/")):
        if other.resolve() == folder.resolve():
            continue
        for py in other.rglob("*.py"):
            for name, h in _function_hashes(py).items():
                for mk, mv in mine.items():
                    if mv == h:
                        warnings.append(
                            f"duplicate: {mk} == {other.name}/{py.name}:{name}; second use -> move to research/signals/ or src/quant/ with a test, in its own PR"
                        )
    return warnings


# --------------------------------------------------------------------------- finish


def finish(folder: Path, owner: str, date: str, dry_run: bool) -> int:
    cfg = yaml.safe_load((folder / "config.yaml").read_text(encoding="utf-8")) or {}
    slug = str(cfg.get("slug") or folder.name)
    outputs = sorted((folder / "outputs").glob("*")) if (folder / "outputs").exists() else []
    result_lines: list[str] = []
    for f in outputs:
        if f.suffix == ".json":
            try:
                obj = json.loads(f.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            result_lines.append(f"From `outputs/{f.name}`:")
            result_lines.append("")
            result_lines.append("```json")
            result_lines.append(json.dumps(obj, indent=2, sort_keys=True))
            result_lines.append("```")
        elif f.suffix in {".txt", ".md", ".csv"} and f.stat().st_size < 20_000:
            result_lines.append(f"From `outputs/{f.name}`:")
            result_lines.append("")
            result_lines.append("```")
            result_lines.append(f.read_text(encoding="utf-8").rstrip())
            result_lines.append("```")
    if not result_lines:
        result_lines = [
            "No files under outputs/. Run the notebook first; --finish quotes outputs only."
        ]
    result_block = "\n".join(result_lines)

    results_path = folder / "results.md"
    text = (
        results_path.read_text(encoding="utf-8")
        if results_path.exists()
        else results_text(slug, owner, date, str(cfg.get("hypothesis", "")))
    )
    if re.search(r"^status:\s*final\s*$", text, flags=re.M):
        print(
            f"{results_path.relative_to(ROOT).as_posix()} is final (frozen); not touching it",
            file=sys.stderr,
        )
        return 1
    new_results = re.sub(
        r"(## Result\n\n)(.*?)(?=\n## |\Z)",
        lambda m: m.group(1) + result_block + "\n",
        text,
        count=1,
        flags=re.S,
    )
    datasets = cfg.get("datasets") or []
    data_lines = [f"- {d.get('name')} at snapshot {d.get('snapshot')}" for d in datasets] or [
        "- none (no curated snapshot named in config.yaml)"
    ]
    tags = ["data"] + (
        ["fx"]
        if any(
            "fx" in str(d.get("name", "")) or "prices" in str(d.get("name", "")) for d in datasets
        )
        else []
    )
    log_id = f"{date}-{slug}"
    log = f"""---
id: {log_id}
type: research-log
title: "{cfg.get("hypothesis", slug).strip().splitlines()[0][:100]}"
date: {date}
authors: [{owner}]
owner: {owner}
status: draft
tags: [{", ".join(tags)}]
datasets: [{", ".join(str(d.get("name")) for d in datasets)}]
related: []
---

# {cfg.get("hypothesis", slug).strip().splitlines()[0][:100]}

## Hypothesis

{cfg.get("hypothesis", "").strip() or "_(fill in from config.yaml)_"}

## Data

{chr(10).join(data_lines)}

## Method

Params from config.yaml: `{json.dumps(cfg.get("params", {}), sort_keys=True)}`; seed {cfg.get("seed")}.
Notebook: [{folder.name}/run.py](../../research/experiments/{folder.name}/run.py).

## Result

{result_block}

## Verdict

_TODO: keep / park / kill, and the one thing you would do next._

## Links

- experiment: [research/experiments/{folder.name}](../../research/experiments/{folder.name}/results.md)
"""
    files = {
        f"research/experiments/{folder.name}/results.md": new_results,
        f"knowledge/research-log/{log_id}.md": log,
    }
    for w in check_dupes(folder):
        print(w, file=sys.stderr)
    if dry_run:
        for rel, t in files.items():
            print(f"--- {rel}")
            print(t, end="")
        return 0
    results_path.write_text(new_results, encoding="utf-8")
    print(results_path.relative_to(ROOT).as_posix())
    log_path = RESEARCH_LOG / f"{log_id}.md"
    if log_path.exists():
        print(f"exists, not overwritten: {log_path.relative_to(ROOT).as_posix()}", file=sys.stderr)
    else:
        log_path.write_text(log, encoding="utf-8")
        print(log_path.relative_to(ROOT).as_posix())
    return 0


# --------------------------------------------------------------------------- main


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="just experiment")
    p.add_argument("slug", help="short-kebab-slug")
    p.add_argument("--owner", default=None)
    p.add_argument("--date", default=None, help="YYYY-MM-DD (default today)")
    p.add_argument(
        "--hypothesis", default="TODO: state the market expectation you are betting against"
    )
    p.add_argument("--dataset", action="append", default=[], help="name:snapshot (repeatable)")
    p.add_argument("--parent", default=None, help="slug of the frozen experiment this follows")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument(
        "--finish",
        action="store_true",
        help="draft results.md and the research-log entry from outputs/",
    )
    p.add_argument("--check-dupes", action="store_true")
    p.add_argument("--dry-run", action="store_true", help="print files instead of writing")
    a = p.parse_args(argv)
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,60}", a.slug):
        print("slug must be short-kebab-case", file=sys.stderr)
        return 2
    owner = a.owner or default_owner()
    date = a.date or dt.date.today().isoformat()
    if a.finish or a.check_dupes:
        matches = (
            sorted(EXPERIMENTS.glob(f"*-{a.slug}"))
            if not (EXPERIMENTS / f"{date}-{a.slug}").exists()
            else [EXPERIMENTS / f"{date}-{a.slug}"]
        )
        if not matches:
            print(f"no experiment folder for slug {a.slug!r}", file=sys.stderr)
            return 1
        folder = matches[-1]
        if a.check_dupes and not a.finish:
            for w in check_dupes(folder):
                print(w)
            return 0
        return finish(folder, owner, date, a.dry_run)
    emit(files_for(a.slug, owner, date, a.hypothesis, a.dataset, a.parent, a.seed), a.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
