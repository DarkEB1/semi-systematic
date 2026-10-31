#!/usr/bin/env python
"""Deterministic part of the new-experiment skill (`just experiment SLUG --project P`).

create:  research/<project>/experiments/<date>-<slug>/{config.yaml, run.py, results.md, figures/};
         run.py is a copy of template_run.py next to this file.
finish:  `--finish` drafts results.md and knowledge/research-log/<date>-<slug>.md from
         config.yaml and the files under outputs/; it never invents a number that is not in outputs/.
dupes:   `--check-dupes` (also run by --finish) flags functions whose source is identical to one in
         another experiment's run.py, in any project: the reuse rule says move it to a tool
         (tools/<name>, see `just new-tool`) on second use, with a test, in its own PR.
         Experiments never import each other (ADR-0003); projects are folders (ADR-0004).
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
RESEARCH = ROOT / "research"
RESEARCH_LOG = ROOT / "knowledge" / "research-log"
TEAM = ROOT / "knowledge" / "context" / "team.yaml"
NOTEBOOK = (Path(__file__).resolve().parent / "template_run.py").read_text(encoding="utf-8")


def projects() -> list[str]:
    if not RESEARCH.exists():
        return []
    return sorted(p.name for p in RESEARCH.iterdir() if (p / "README.md").exists())


def experiment_dirs() -> list[Path]:
    return sorted(p for p in RESEARCH.glob("*/experiments/*/") if p.is_dir())


def default_owner() -> str:
    if os.getenv("R2_HANDLE"):
        return os.environ["R2_HANDLE"]
    team = yaml.safe_load(TEAM.read_text(encoding="utf-8")) if TEAM.exists() else {}
    return str(
        (team or {}).get("data_layer_owner") or ((team or {}).get("handles") or ["unknown"])[0]
    )


# --------------------------------------------------------------------------- scaffold


def config_text(
    slug: str,
    project: str,
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
        "project": project,
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
    project: str,
    owner: str,
    date: str,
    hypothesis: str,
    datasets: list[str],
    parent: str | None,
    seed: int,
) -> dict[str, str]:
    folder = f"research/{project}/experiments/{date}-{slug}"
    return {
        f"{folder}/config.yaml": config_text(
            slug, project, owner, date, hypothesis, datasets, parent, seed
        ),
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
    for other in experiment_dirs():
        if other.resolve() == folder.resolve():
            continue
        other_rel = other.relative_to(RESEARCH).as_posix()
        for py in other.rglob("*.py"):
            for name, h in _function_hashes(py).items():
                for mk, mv in mine.items():
                    if mv == h:
                        warnings.append(
                            f"duplicate: {mk} == {other_rel}/{py.name}:{name}; second use -> move to a tool (tools/<name>, `just new-tool`) with a test, in its own PR"
                        )
    return warnings


# --------------------------------------------------------------------------- finish


def result_block(folder: Path) -> str:
    """The Result section: every quotable file under outputs/, verbatim; never a typed number."""
    outputs = sorted((folder / "outputs").glob("*")) if (folder / "outputs").exists() else []
    lines: list[str] = []
    for f in outputs:
        if f.suffix == ".json":
            try:
                obj = json.loads(f.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            body, fence = json.dumps(obj, indent=2, sort_keys=True), "```json"
        elif f.suffix in {".txt", ".md", ".csv"} and f.stat().st_size < 20_000:
            body, fence = f.read_text(encoding="utf-8").rstrip(), "```"
        else:
            continue
        lines += [f"From `outputs/{f.name}`:", "", fence, body, "```"]
    if not lines:
        lines = ["No files under outputs/. Run the notebook first; --finish quotes outputs only."]
    return "\n".join(lines)


def log_text(cfg: dict, folder: Path, owner: str, date: str, result: str) -> tuple[str, str]:
    """The research-log entry drafted from config.yaml and the Result block; returns (id, text)."""
    slug = str(cfg.get("slug") or folder.name)
    project = str(cfg.get("project") or folder.parent.parent.name)
    folder_rel = folder.relative_to(ROOT).as_posix()
    datasets = cfg.get("datasets") or []
    data_lines = [f"- {d.get('name')} at snapshot {d.get('snapshot')}" for d in datasets] or [
        "- none (no curated snapshot named in config.yaml)"
    ]
    names = [str(d.get("name", "")) for d in datasets]
    tags = ["data"] + (["fx"] if any("fx" in n or "prices" in n for n in names) else [])
    log_id = f"{date}-{slug}"
    title = cfg.get("hypothesis", slug).strip().splitlines()[0][:100]
    text = f"""---
id: {log_id}
type: research-log
title: "{title}"
date: {date}
authors: [{owner}]
owner: {owner}
status: draft
tags: [{", ".join(tags)}]
datasets: [{", ".join(names)}]
project: {project}
related: [{project}]
---

# {title}

## Hypothesis

{cfg.get("hypothesis", "").strip() or "_(fill in from config.yaml)_"}

## Data

{chr(10).join(data_lines)}

## Method

Params from config.yaml: `{json.dumps(cfg.get("params", {}), sort_keys=True)}`; seed {cfg.get("seed")}.
Notebook: [{folder.name}/run.py](../../{folder_rel}/run.py).

## Result

{result}

## Verdict

_TODO: keep / park / kill, and the one thing you would do next._

## Links

- project: [research/{project}](../../research/{project}/README.md)
- experiment: [{folder_rel}](../../{folder_rel}/results.md)
"""
    return log_id, text


def finish(folder: Path, owner: str, date: str, dry_run: bool) -> int:
    cfg = yaml.safe_load((folder / "config.yaml").read_text(encoding="utf-8")) or {}
    slug = str(cfg.get("slug") or folder.name)
    folder_rel = folder.relative_to(ROOT).as_posix()
    results_path = folder / "results.md"
    text = (
        results_path.read_text(encoding="utf-8")
        if results_path.exists()
        else results_text(slug, owner, date, str(cfg.get("hypothesis", "")))
    )
    if re.search(r"^status:\s*final\s*$", text, flags=re.M):
        print(f"{folder_rel}/results.md is final (frozen); not touching it", file=sys.stderr)
        return 1
    result = result_block(folder)
    new_results = re.sub(
        r"(## Result\n\n)(.*?)(?=\n## |\Z)",
        lambda m: m.group(1) + result + "\n",
        text,
        count=1,
        flags=re.S,
    )
    log_id, log = log_text(cfg, folder, owner, date, result)
    for w in check_dupes(folder):
        print(w, file=sys.stderr)
    if dry_run:
        for rel, t in {
            f"{folder_rel}/results.md": new_results,
            f"knowledge/research-log/{log_id}.md": log,
        }.items():
            print(f"--- {rel}")
            print(t, end="")
        return 0
    results_path.write_text(new_results, encoding="utf-8")
    print(f"{folder_rel}/results.md")
    log_path = RESEARCH_LOG / f"{log_id}.md"
    if log_path.exists():
        print(f"exists, not overwritten: {log_path.relative_to(ROOT).as_posix()}", file=sys.stderr)
    else:
        log_path.write_text(log, encoding="utf-8")
        print(log_path.relative_to(ROOT).as_posix())
    return 0


# --------------------------------------------------------------------------- main


def find_folder(slug: str, project: str | None, date: str) -> Path | None:
    roots = [RESEARCH / project / "experiments"] if project else [RESEARCH]
    pattern = f"{date}-{slug}" if project else f"*/experiments/{date}-{slug}"
    exact = [p for r in roots for p in r.glob(pattern) if p.is_dir()]
    if exact:
        return exact[-1]
    loose = f"*-{slug}" if project else f"*/experiments/*-{slug}"
    matches = sorted(p for r in roots for p in r.glob(loose) if p.is_dir())
    return matches[-1] if matches else None


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="just experiment")
    p.add_argument("slug", help="short-kebab-slug")
    p.add_argument(
        "--project", default=None, help="project folder under research/ (required to create)"
    )
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
    return p


def main(argv: list[str] | None = None) -> int:
    a = parser().parse_args(argv)
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,60}", a.slug):
        print("slug must be short-kebab-case", file=sys.stderr)
        return 2
    owner = a.owner or default_owner()
    date = a.date or dt.date.today().isoformat()
    if a.finish or a.check_dupes:
        folder = find_folder(a.slug, a.project, date)
        if folder is None:
            print(
                f"no experiment folder for slug {a.slug!r} under research/*/experiments/",
                file=sys.stderr,
            )
            return 1
        if a.check_dupes and not a.finish:
            for w in check_dupes(folder):
                print(w)
            return 0
        return finish(folder, owner, date, a.dry_run)
    known = projects()
    if not a.project:
        print(
            "--project is required: "
            + (", ".join(known) if known else "none yet")
            + "; `just project <slug>` creates one",
            file=sys.stderr,
        )
        return 2
    if a.project not in known and not a.dry_run:
        print(
            f"no project research/{a.project}/README.md; `just project {a.project}` creates it"
            + (f" (existing: {', '.join(known)})" if known else ""),
            file=sys.stderr,
        )
        return 2
    emit(
        files_for(a.slug, a.project, owner, date, a.hypothesis, a.dataset, a.parent, a.seed),
        a.dry_run,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
