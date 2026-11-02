"""The schema contract: the Schema table of ``catalog/datasets/<name>.md`` is the contract for
``curated/<name>/``. Raw has no contract."""

from __future__ import annotations

import re

import pyarrow as pa

from quant.data._paths import DATASET_DOCS, REPO_ROOT

_ARROW_TYPES: dict[str, pa.DataType] = {
    "string": pa.string(),
    "str": pa.string(),
    "utf8": pa.string(),
    "date": pa.date32(),
    "date32": pa.date32(),
    "timestamp": pa.timestamp("us"),
    "timestamp[us]": pa.timestamp("us"),
    "timestamp[us, utc]": pa.timestamp("us", tz="UTC"),
    "timestamp[utc]": pa.timestamp("us", tz="UTC"),
    "timestamp[ms]": pa.timestamp("ms"),
    "timestamp[ns]": pa.timestamp("ns"),
    "float64": pa.float64(),
    "double": pa.float64(),
    "float32": pa.float32(),
    "float": pa.float64(),
    "int64": pa.int64(),
    "int32": pa.int32(),
    "int": pa.int64(),
    "bool": pa.bool_(),
    "boolean": pa.bool_(),
}


class SchemaMismatch(ValueError):
    """Raised when a Parquet file does not match the README schema of a curated dataset."""


def _schema_table(md: str) -> list[dict[str, str]]:
    """Rows of the markdown table under the ``## Schema`` heading."""
    m = re.search(r"^## Schema\s*$(.*?)(?=^## |\Z)", md, flags=re.M | re.S)
    if not m:
        raise SchemaMismatch("README has no '## Schema' section")
    rows = [ln.strip() for ln in m.group(1).splitlines() if ln.strip().startswith("|")]
    if len(rows) < 2:
        raise SchemaMismatch("Schema section has no table")
    header = [c.strip().lower() for c in rows[0].strip("|").split("|")]
    out = []
    for ln in rows[2:]:  # skip header and separator
        cells = [c.strip() for c in ln.strip("|").split("|")]
        if len(cells) != len(header):
            continue
        out.append(dict(zip(header, cells, strict=True)))
    return out


def schema_from_readme(name: str) -> pa.Schema:
    """Parse the Schema table of ``catalog/datasets/<name>.md`` into a pyarrow schema.

    The table needs ``column`` and ``type`` headers (``units`` and ``description`` are kept as
    field metadata). Types: string, date, timestamp, float64, float32, int64, int32, bool.
    """
    path = DATASET_DOCS / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"no dataset README at {path.relative_to(REPO_ROOT)}")
    fields = []
    for row in _schema_table(path.read_text(encoding="utf-8")):
        col = row.get("column", "").strip("`")
        typ = row.get("type", "").strip("`").lower()
        if typ not in _ARROW_TYPES:
            raise SchemaMismatch(f"{name}: unknown type {typ!r} for column {col!r}")
        meta = {k: v for k, v in row.items() if k not in {"column", "type"} and v}
        fields.append(pa.field(col, _ARROW_TYPES[typ], nullable=True, metadata=meta or None))
    if not fields:
        raise SchemaMismatch(f"{name}: empty schema table")
    return pa.schema(fields)


def validate_schema(table: pa.Table, name: str) -> None:
    """Raise ``SchemaMismatch`` unless the table's columns and types equal the README schema."""
    expected = schema_from_readme(name)
    got = table.schema
    problems = []
    exp_names = expected.names
    got_names = got.names
    if sorted(exp_names) != sorted(got_names):
        missing = sorted(set(exp_names) - set(got_names))
        extra = sorted(set(got_names) - set(exp_names))
        problems.append(f"columns differ: missing={missing} extra={extra}")
    for f in expected:
        if f.name in got_names and got.field(f.name).type != f.type:
            problems.append(f"{f.name}: expected {f.type}, got {got.field(f.name).type}")
    if problems:
        raise SchemaMismatch(
            f"{name} does not match catalog/datasets/{name}.md: " + "; ".join(problems)
        )
