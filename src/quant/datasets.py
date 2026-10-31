"""Read the structured bits of ``catalog/datasets/<name>.md`` (frontmatter plus the
``- key: value`` lines in the Source and Cadence sections). Shared by data-health, the audit,
the refresh-data skill and the dashboard."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from quant import data

_FM = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)
_KV = re.compile(r"^\s*-\s*([a-z_]+)\s*:\s*(.+?)\s*$", re.M)


@dataclass
class DatasetDoc:
    name: str
    path: Path
    owner: str
    source: str
    cadence: str
    lag_days: int
    frontmatter: dict = field(default_factory=dict)

    @property
    def raw_prefix(self) -> str:
        return f"{data.RAW}{self.source}/{self.name}/"

    @property
    def curated_prefix(self) -> str:
        return f"{data.CURATED}{self.name}/"


def _section(md: str, heading: str) -> str:
    m = re.search(rf"^## {re.escape(heading)}\s*$(.*?)(?=^## |\Z)", md, flags=re.M | re.S)
    return m.group(1) if m else ""


def parse_dataset_doc(path: Path) -> DatasetDoc:
    md = path.read_text(encoding="utf-8")
    fm_match = _FM.match(md)
    fm = yaml.safe_load(fm_match.group(1)) if fm_match else {}
    src = dict(_KV.findall(_section(md, "Source")))
    cad = dict(_KV.findall(_section(md, "Cadence")))
    return DatasetDoc(
        name=path.stem,
        path=path,
        owner=str(fm.get("owner", "")),
        source=src.get("source", ""),
        cadence=cad.get("cadence", "daily"),
        lag_days=int(cad.get("lag_days", 1)),
        frontmatter=fm or {},
    )


def dataset_docs() -> list[DatasetDoc]:
    return [parse_dataset_doc(p) for p in sorted(data.DATASET_DOCS.glob("*.md"))]
