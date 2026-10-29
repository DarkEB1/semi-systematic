"""Build .index/chunks.parquet over the repo.

All chunking logic is in one function, ``chunk(path, text) -> list[Chunk]``, so it can be replaced
later (e.g. by a token-aware splitter) without touching collection or output. Sources walked:

- knowledge/**/*.md (skipping ``private: true``, templates and INDEX.md)
- catalog/datasets/*.md
- research/experiments/*/config.yaml and results.md
- every .claude/skills/*/SKILL.md
- src/**/*.py and research/signals/**/*.py (one chunk per top-level function/class, docstring first)

Markdown is chunked on ``##``. There is no embedding column yet; see ``embed.py``.
"""

from __future__ import annotations

import ast
import datetime as dt
import hashlib
import re
import subprocess
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import yaml

ROOT = Path(__file__).resolve().parents[3]
INDEX_DIR = ROOT / ".index"
INDEX_FILE = INDEX_DIR / "chunks.parquet"
FM_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z", re.S)


@dataclass
class Chunk:
    source: str  # constant 'repo' for now
    chunk_id: str
    path: str
    type: str
    title: str
    date: str | None
    authors: list[str] = field(default_factory=list)
    owner: str | None = None
    tags: list[str] = field(default_factory=list)
    datasets: list[str] = field(default_factory=list)
    status: str | None = None
    heading: str = ""
    text: str = ""
    git_sha: str = ""
    last_modified: str = ""


SCHEMA = pa.schema(
    [
        ("source", pa.string()),
        ("chunk_id", pa.string()),
        ("path", pa.string()),
        ("type", pa.string()),
        ("title", pa.string()),
        ("date", pa.string()),
        ("authors", pa.list_(pa.string())),
        ("owner", pa.string()),
        ("tags", pa.list_(pa.string())),
        ("datasets", pa.list_(pa.string())),
        ("status", pa.string()),
        ("heading", pa.string()),
        ("text", pa.string()),
        ("git_sha", pa.string()),
        ("last_modified", pa.string()),
    ]
)


# --------------------------------------------------------------------------- helpers


def _split_frontmatter(text: str) -> tuple[dict, str]:
    m = FM_RE.match(text)
    if not m:
        return {}, text
    try:
        fm = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        return {}, text
    return (fm if isinstance(fm, dict) else {}), m.group(2)


def _aslist(v) -> list[str]:
    if v is None:
        return []
    if isinstance(v, list):
        return [str(x) for x in v]
    return [str(v)]


def _cid(path: str, heading: str, n: int) -> str:
    return hashlib.sha1(f"{path}#{n}:{heading}".encode()).hexdigest()[:16]


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _h1(body: str) -> str | None:
    m = re.search(r"^# (.+)$", body, flags=re.M)
    return m.group(1).strip() if m else None


# --------------------------------------------------------------------------- chunk()


def chunk(path: Path, text: str) -> list[Chunk]:
    """The single chunking function. Replace this to change how everything is split."""
    rel = _rel(path)
    name = path.name
    if name.endswith(".md"):
        return _chunk_markdown(rel, path, text)
    if name == "config.yaml":
        return _chunk_experiment_config(rel, text)
    if name.endswith(".py"):
        return _chunk_python(rel, text)
    return []


def _chunk_markdown(rel: str, path: Path, text: str) -> list[Chunk]:
    fm, body = _split_frontmatter(text)
    if fm.get("private") is True:
        return []
    if path.name == "SKILL.md":
        typ = "skill"
        title = str(fm.get("name") or _h1(body) or path.parent.name)
    elif path.name == "results.md" and "research/experiments/" in rel:
        typ = "results"
        title = str(fm.get("title") or _h1(body) or path.parent.name)
    else:
        typ = str(fm.get("type") or "doc")
        title = str(fm.get("title") or _h1(body) or path.stem)
    meta = dict(
        source="repo",
        path=rel,
        type=typ,
        title=title,
        date=str(fm["date"]) if fm.get("date") else None,
        authors=_aslist(fm.get("authors")),
        owner=str(fm["owner"]) if fm.get("owner") else None,
        tags=_aslist(fm.get("tags")),
        datasets=_aslist(fm.get("datasets")),
        status=str(fm["status"]) if fm.get("status") else None,
    )
    out: list[Chunk] = []
    heading, buf = "", []
    n = 0

    def flush() -> None:
        nonlocal n
        t = "\n".join(buf).strip()
        if t:
            out.append(Chunk(chunk_id=_cid(rel, heading, n), heading=heading, text=t, **meta))
            n += 1

    in_fence = False
    for ln in body.splitlines():
        if ln.strip().startswith("```"):
            in_fence = not in_fence
        if not in_fence and ln.startswith("## "):
            flush()
            heading, buf = ln[3:].strip(), []
            continue
        buf.append(ln)
    flush()
    return out


def _chunk_experiment_config(rel: str, text: str) -> list[Chunk]:
    try:
        cfg = yaml.safe_load(text) or {}
    except yaml.YAMLError:
        cfg = {}
    slug = str(cfg.get("slug") or Path(rel).parent.name)
    return [
        Chunk(
            source="repo",
            chunk_id=_cid(rel, "config", 0),
            path=rel,
            type="experiment",
            title=slug,
            date=str(cfg.get("date"))
            if cfg.get("date")
            else _date_from_name(Path(rel).parent.name),
            authors=_aslist(cfg.get("owner")),
            owner=str(cfg["owner"]) if cfg.get("owner") else None,
            tags=_aslist(cfg.get("tags")),
            datasets=[
                str(d.get("name")) for d in (cfg.get("datasets") or []) if isinstance(d, dict)
            ],
            status=str(cfg.get("status")) if cfg.get("status") else None,
            heading="config",
            text=text.strip(),
        )
    ]


def _date_from_name(name: str) -> str | None:
    m = re.match(r"(\d{4}-\d{2}-\d{2})", name)
    return m.group(1) if m else None


def _chunk_python(rel: str, text: str) -> list[Chunk]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return [
            Chunk(
                "repo",
                _cid(rel, "module", 0),
                rel,
                "code",
                Path(rel).stem,
                None,
                heading="module",
                text=text[:4000],
            )
        ]
    lines = text.splitlines()
    out: list[Chunk] = []
    mod_doc = ast.get_docstring(tree) or ""
    if mod_doc:
        out.append(
            Chunk(
                "repo",
                _cid(rel, "module", 0),
                rel,
                "code",
                Path(rel).stem,
                None,
                heading="module",
                text=mod_doc,
            )
        )
    n = 1
    for node in tree.body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            doc = ast.get_docstring(node) or ""
            start = (node.decorator_list[0].lineno if node.decorator_list else node.lineno) - 1
            src = "\n".join(lines[start : node.end_lineno])
            body_text = (doc + "\n\n" if doc else "") + src
            out.append(
                Chunk(
                    "repo",
                    _cid(rel, node.name, n),
                    rel,
                    "code",
                    Path(rel).stem,
                    None,
                    heading=node.name,
                    text=body_text,
                )
            )
            n += 1
    return out


# --------------------------------------------------------------------------- collect / build


def collect(root: Path = ROOT) -> list[Path]:
    paths: list[Path] = []
    kn = root / "knowledge"
    if kn.exists():
        for p in kn.rglob("*.md"):
            rp = p.relative_to(root).parts
            if "templates" in rp or p.name == "INDEX.md" or ".obsidian" in rp:
                continue
            paths.append(p)
    paths += sorted((root / "catalog" / "datasets").glob("*.md"))
    for exp in sorted((root / "research" / "experiments").glob("*/")):
        for nm in ("config.yaml", "results.md"):
            if (exp / nm).exists():
                paths.append(exp / nm)
    paths += sorted((root / ".claude" / "skills").glob("*/SKILL.md"))
    paths += sorted(p for p in (root / "src").rglob("*.py") if "__pycache__" not in p.parts)
    paths += sorted(
        p for p in (root / "research" / "signals").rglob("*.py") if "__pycache__" not in p.parts
    )
    return sorted(set(paths))


def git_sha(root: Path = ROOT) -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=True
        ).stdout.strip()
    except Exception:  # noqa: BLE001
        return ""


def build(root: Path = ROOT, out: Path = INDEX_FILE) -> int:
    sha = git_sha(root)
    chunks: list[Chunk] = []
    for p in collect(root):
        text = p.read_text(encoding="utf-8", errors="replace")
        mtime = dt.datetime.fromtimestamp(p.stat().st_mtime, tz=dt.UTC).isoformat(
            timespec="seconds"
        )
        for c in chunk(p, text):
            c.git_sha, c.last_modified = sha, mtime
            chunks.append(c)
    cols = {f.name: [getattr(c, f.name) for c in chunks] for f in fields(Chunk)}
    table = pa.Table.from_pydict(cols, schema=SCHEMA)
    out.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, out, compression="zstd")
    return len(chunks)


def to_records(chunks: list[Chunk]) -> list[dict]:
    return [asdict(c) for c in chunks]
