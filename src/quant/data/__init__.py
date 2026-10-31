"""Data layer: one DuckDB connection, one write path, one set of prefix rules.

Bucket prefix rules (the same text lives in src/quant/AGENTS.md; change both together):

- ``raw/``                 written only by ingest.yml (``QUANT_ROLE=ingest``). A partition may be
                           overwritten in place, and only here is ``overwrite=True`` accepted.
- ``curated/``             written only by promote.yml (``QUANT_ROLE=promote``). Never overwritten.
                           The schema contract (``schema_from_readme``) applies here only.
- ``scratch/<handle>/``    the only prefix a person or an agent writes, from a laptop or a sandbox
                           (``QUANT_ROLE`` unset). ``<handle>`` is ``R2_HANDLE``.

Partitioning (``quant.data.keys``):

- daily datasets           ``<dataset>/year=YYYY/month=MM/data.parquet``
- intraday datasets        ``<dataset>/date=YYYY-MM-DD/<asset_class>.parquet`` (one file per day per asset class)
- curated snapshots        ``<dataset>/snapshot=YYYY-MM-DD/data.parquet``

Raw is stored as received (no schema contract, ``quant.data.schema``). Catalog views are named
``<source>_<dataset>`` for raw and plain ``<dataset>`` for curated.
"""

from __future__ import annotations

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

from quant.data._paths import CATALOG_SQL, DATASET_DOCS, REPO_ROOT
from quant.data.keys import partition_key, partition_parts
from quant.data.schema import SchemaMismatch, schema_from_readme, validate_schema

__all__ = [
    "CATALOG_SQL",
    "CURATED",
    "DATASET_DOCS",
    "RAW",
    "REPO_ROOT",
    "SCRATCH",
    "ExistsError",
    "PrefixError",
    "SchemaMismatch",
    "Settings",
    "check_write_allowed",
    "connect",
    "list_keys",
    "load",
    "partition_key",
    "partition_parts",
    "put_text",
    "read_parquet",
    "s3_client",
    "schema_from_readme",
    "settings",
    "validate_schema",
    "write_once",
]

RAW = "raw/"
CURATED = "curated/"
SCRATCH = "scratch/"

ROLE_PREFIX = {"ingest": RAW, "promote": CURATED}


class PrefixError(PermissionError):
    """Raised when a write targets a prefix the current role may not write."""


class ExistsError(FileExistsError):
    """Raised when a write would overwrite an existing object without permission."""


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
    cfg: dict[str, Any] = (
        config
        if isinstance(config, dict)
        else yaml.safe_load(Path(config).read_text(encoding="utf-8"))
    )
    s = settings()
    con = connect(views=False)
    out: dict[str, pa.Table] = {}
    for item in cfg.get("datasets", []) or []:
        name, snap = item["name"], str(item["snapshot"])
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", snap):
            raise ValueError(f"{name}: snapshot must be YYYY-MM-DD, got {snap!r}")
        url = f"s3://{s.bucket}/curated/{name}/snapshot={snap}/*.parquet"
        try:
            out[name] = con.execute("SELECT * FROM read_parquet(?)", [url]).arrow()
        except Exception as e:  # noqa: BLE001
            raise FileNotFoundError(f"{name} snapshot {snap} not found at {url}: {e}") from e
    return out
