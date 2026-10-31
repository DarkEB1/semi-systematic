"""Object keys: hive-style partition directories and the file name per cadence."""

from __future__ import annotations

import datetime as dt
from typing import Any


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
