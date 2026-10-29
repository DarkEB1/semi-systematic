"""Data layer: one DuckDB connection, one write path, one set of prefix rules.

Bucket prefix rules (the same text lives in AGENTS.md; change both together):

- ``raw/``                 written only by ingest.yml (``QUANT_ROLE=ingest``). A partition may be
                           overwritten in place, and only here is ``overwrite=True`` accepted.
- ``curated/``             written only by promote.yml (``QUANT_ROLE=promote``). Never overwritten.
                           The schema contract (``schema_from_readme``) applies here only.
- ``scratch/<handle>/``    the only prefix a person or an agent writes, from a laptop or a sandbox
                           (``QUANT_ROLE`` unset). ``<handle>`` is ``R2_HANDLE``.

Partitioning:

- daily datasets           ``<dataset>/year=YYYY/month=MM/data.parquet``
- intraday datasets        ``<dataset>/date=YYYY-MM-DD/<asset_class>.parquet`` (one file per day per asset class)
- curated snapshots        ``<dataset>/snapshot=YYYY-MM-DD/data.parquet``

Raw is stored as received (no schema contract). Catalog views are named ``<source>_<dataset>``
for raw and plain ``<dataset>`` for curated.
"""

from __future__ import annotations

import datetime as dt
import io
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
import yaml
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[3]
CATALOG_SQL = REPO_ROOT / "catalog" / "catalog.sql"
DATASET_DOCS = REPO_ROOT / "catalog" / "datasets"

RAW = "raw/"
CURATED = "curated/"
SCRATCH = "scratch/"

ROLE_PREFIX = {"ingest": RAW, "promote": CURATED}

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


class PrefixError(PermissionError):
    """Raised when a write targets a prefix the current role may not write."""


class ExistsError(FileExistsError):
    """Raised when a write would overwrite an existing object without permission."""


class SchemaMismatch(ValueError):
    """Raised when a Parquet file does not match the README schema of a curated dataset."""


# --------------------------------------------------------------------------- settings


@dataclass(frozen=True)
class Settings:
    account_id: str
    endpoint: str
    bucket: str
    access_key_id: str
    secret_access_key: str
    handle: str
    role: str  # "ingest" | "promote" | "user"

    @property
    def allowed_prefix(self) -> str:
        if self.role in ROLE_PREFIX:
            return ROLE_PREFIX[self.role]
        if not self.handle:
            raise PrefixError("R2_HANDLE is not set; scratch writes need a handle")
        return f"{SCRATCH}{self.handle}/"


def settings(*, write: bool = False) -> Settings:
    """Read settings from the environment (and .env at the repo root).

    With ``write=True`` and no role, the scratch key pair is used when present, because the
    team-read key cannot write anything.
    """
    load_dotenv(REPO_ROOT / ".env", override=False)
    role = (os.getenv("QUANT_ROLE") or "user").strip().lower()
    key = os.getenv("R2_ACCESS_KEY_ID", "")
    secret = os.getenv("R2_SECRET_ACCESS_KEY", "")
    if write and role not in ROLE_PREFIX and os.getenv("R2_SCRATCH_ACCESS_KEY_ID"):
        key = os.environ["R2_SCRATCH_ACCESS_KEY_ID"]
        secret = os.getenv("R2_SCRATCH_SECRET_ACCESS_KEY", "")
    return Settings(
        account_id=os.getenv("R2_ACCOUNT_ID", ""),
        endpoint=os.getenv("R2_ENDPOINT", ""),
        bucket=os.getenv("R2_BUCKET", ""),
        access_key_id=key,
        secret_access_key=secret,
        handle=os.getenv("R2_HANDLE", ""),
        role=role,
    )


def s3_client(*, write: bool = False) -> Any:
    """A boto3 S3 client against R2. Imported lazily so tests can inject a fake client."""
    import boto3
    from botocore.config import Config

    s = settings(write=write)
    missing = [
        n for n, v in (("R2_ENDPOINT", s.endpoint), ("R2_ACCESS_KEY_ID", s.access_key_id)) if not v
    ]
    if missing:
        raise OSError(f"missing environment variables: {', '.join(missing)} (see .env.example)")
    return boto3.client(
        "s3",
        endpoint_url=s.endpoint,
        aws_access_key_id=s.access_key_id,
        aws_secret_access_key=s.secret_access_key,
        region_name="auto",
        config=Config(signature_version="s3v4", retries={"max_attempts": 3}),
    )


# --------------------------------------------------------------------------- keys


def partition_key(dataset: str, **parts: Any) -> str:
    """Hive-style partition directory, e.g. ``partition_key("prices_daily", year=2026, month=10)``
    -> ``prices_daily/year=2026/month=10``. Values are formatted as given; pass ``month="10"``
    or an int, both become ``month=10``; ``month=3`` becomes ``month=03``."""
    segs = [dataset.strip("/")]
    for k, v in parts.items():
        if k == "month" and isinstance(v, int):
            v = f"{v:02d}"
        segs.append(f"{k}={v}")
    return "/".join(segs)


def partition_parts(
    cadence: str, day: dt.date, *, asset_class: str | None = None
) -> tuple[dict[str, Any], str]:
    """Partition parts and file name for a cadence: daily -> year/month, intraday -> date,
    snapshot -> snapshot."""
    if cadence == "daily":
        return {"year": day.year, "month": day.month}, "data.parquet"
    if cadence == "intraday":
        if not asset_class:
            raise ValueError(
                "intraday partitions need an asset_class (one file per day per asset class)"
            )
        return {"date": day.isoformat()}, f"{asset_class}.parquet"
    if cadence == "snapshot":
        return {"snapshot": day.isoformat()}, "data.parquet"
    raise ValueError(f"unknown cadence {cadence!r} (daily, intraday, snapshot)")


# --------------------------------------------------------------------------- writes


def check_write_allowed(key: str, *, overwrite: bool = False, cfg: Settings | None = None) -> None:
    """Enforce the prefix rules. Raises ``PrefixError`` or ``ValueError``; returns None if fine."""
    cfg = cfg or settings(write=True)
    if key.startswith("/") or ".." in key.split("/"):
        raise ValueError(f"bad key {key!r}")
    allowed = cfg.allowed_prefix
    if not key.startswith(allowed):
        raise PrefixError(
            f"role {cfg.role!r} may write only under {allowed!r}; refused {key!r}. "
            "raw/ is written by ingest.yml, curated/ by promote.yml, people and agents write scratch/<handle>/."
        )
    if overwrite and not key.startswith(RAW):
        raise ValueError(f"overwrite=True is accepted only for keys under {RAW!r}; refused {key!r}")


def _to_arrow(table: Any) -> pa.Table:
    if isinstance(table, pa.Table):
        return table
    if hasattr(table, "to_arrow"):  # polars
        return table.to_arrow()
    raise TypeError(f"expected a pyarrow.Table or polars.DataFrame, got {type(table).__name__}")


def _exists(client: Any, bucket: str, key: str) -> bool:
    from botocore.exceptions import ClientError

    try:
        client.head_object(Bucket=bucket, Key=key)
        return True
    except ClientError as e:  # pragma: no cover - exercised through the fake client in tests
        code = str(e.response.get("Error", {}).get("Code", ""))
        if code in {"404", "NoSuchKey", "NotFound"}:
            return False
        raise


def write_once(
    table: Any,
    key: str,
    overwrite: bool = False,
    *,
    client: Any = None,
    cfg: Settings | None = None,
) -> str:
    """Write a Parquet object exactly once.

    Refuses to overwrite an existing object. ``overwrite=True`` is accepted only for keys under
    ``raw/`` and raises ``ValueError`` otherwise. The current role must be allowed to write the
    key's prefix (``PrefixError`` otherwise). Returns the key.
    """
    cfg = cfg or settings(write=True)
    check_write_allowed(key, overwrite=overwrite, cfg=cfg)
    client = client or s3_client(write=True)
    if not overwrite and _exists(client, cfg.bucket, key):
        raise ExistsError(
            f"s3://{cfg.bucket}/{key} already exists and overwrite is not allowed here"
        )
    buf = io.BytesIO()
    pq.write_table(_to_arrow(table), buf, compression="zstd")
    client.put_object(
        Bucket=cfg.bucket,
        Key=key,
        Body=buf.getvalue(),
        ContentType="application/vnd.apache.parquet",
    )
    return key


def put_text(
    text: str,
    key: str,
    *,
    client: Any = None,
    cfg: Settings | None = None,
    content_type: str = "text/markdown",
) -> str:
    """Write a small text object (dataset README next to a curated snapshot). Same prefix rules, never overwrites."""
    cfg = cfg or settings(write=True)
    check_write_allowed(key, cfg=cfg)
    client = client or s3_client(write=True)
    if _exists(client, cfg.bucket, key):
        raise ExistsError(f"s3://{cfg.bucket}/{key} already exists")
    client.put_object(
        Bucket=cfg.bucket, Key=key, Body=text.encode("utf-8"), ContentType=content_type
    )
    return key


def list_keys(
    prefix: str = "", *, client: Any = None, cfg: Settings | None = None
) -> list[dict[str, Any]]:
    """All objects under a prefix as dicts with Key, Size, LastModified."""
    cfg = cfg or settings()
    client = client or s3_client()
    out: list[dict[str, Any]] = []
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=cfg.bucket, Prefix=prefix):
        out.extend(page.get("Contents", []))
    return out


def read_parquet(key: str, *, client: Any = None, cfg: Settings | None = None) -> pa.Table:
    cfg = cfg or settings()
    client = client or s3_client()
    body = client.get_object(Bucket=cfg.bucket, Key=key)["Body"].read()
    return pq.read_table(io.BytesIO(body))


# --------------------------------------------------------------------------- schema contract


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


# --------------------------------------------------------------------------- duckdb


def _catalog_statements(bucket: str) -> list[str]:
    sql = CATALOG_SQL.read_text(encoding="utf-8")
    sql = sql.replace("{bucket}", bucket).replace("{repo}", REPO_ROOT.as_posix())
    return [
        s.strip() for s in re.split(r";\s*\n", sql) if s.strip() and not s.strip().startswith("--")
    ]


def connect(*, strict: bool = False, views: bool = True) -> Any:
    """A DuckDB connection with httpfs loaded, an S3 secret from the environment and every view in
    ``catalog/catalog.sql`` created. Views whose files do not exist yet are skipped with a notice
    unless ``strict=True``."""
    import duckdb

    s = settings()
    con = duckdb.connect()
    con.execute("INSTALL httpfs; LOAD httpfs;")
    if s.access_key_id and s.endpoint:
        host = re.sub(r"^https?://", "", s.endpoint).rstrip("/")
        con.execute(
            "CREATE OR REPLACE SECRET r2 (TYPE S3, KEY_ID ?, SECRET ?, ENDPOINT ?, REGION 'auto', URL_STYLE 'path', USE_SSL true)",
            [s.access_key_id, s.secret_access_key, host],
        )
    if views and CATALOG_SQL.exists():
        for stmt in _catalog_statements(s.bucket):
            try:
                con.execute(stmt)
            except Exception as e:  # noqa: BLE001 - a missing partition is expected on day one
                if strict:
                    raise
                name = re.search(r"VIEW\s+(\w+)", stmt)
                print(
                    f"[quant.data] view {name.group(1) if name else '?'} skipped: {str(e).splitlines()[0]}",
                    file=sys.stderr,
                )
    return con


# --------------------------------------------------------------------------- experiments


def load(config: str | os.PathLike[str] | dict[str, Any]) -> dict[str, pa.Table]:
    """Read an experiment ``config.yaml`` and return only the named datasets at the named snapshots.

    ``datasets:`` is a list of ``{name: prices_daily, snapshot: 2026-10-29}``. Each is read from
    ``curated/<name>/snapshot=<snapshot>/``; a missing snapshot is an error, never silently the latest.
    """
    if not isinstance(config, dict):
        config = yaml.safe_load(Path(config).read_text(encoding="utf-8"))
    s = settings()
    con = connect(views=False)
    out: dict[str, pa.Table] = {}
    for item in config.get("datasets", []) or []:
        name, snap = item["name"], str(item["snapshot"])
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", snap):
            raise ValueError(f"{name}: snapshot must be YYYY-MM-DD, got {snap!r}")
        url = f"s3://{s.bucket}/curated/{name}/snapshot={snap}/*.parquet"
        try:
            out[name] = con.execute("SELECT * FROM read_parquet(?)", [url]).arrow()
        except Exception as e:  # noqa: BLE001
            raise FileNotFoundError(f"{name} snapshot {snap} not found at {url}: {e}") from e
    return out
