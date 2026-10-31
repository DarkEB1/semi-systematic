"""Repo paths the data layer reads: the catalog SQL and the dataset READMEs."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
CATALOG_SQL = REPO_ROOT / "catalog" / "catalog.sql"
DATASET_DOCS = REPO_ROOT / "catalog" / "datasets"
