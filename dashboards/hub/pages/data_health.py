"""Data-health page: each raw dataset's latest partition vs the cadence in catalog/datasets/*.md.
Same logic as `just data-health` (quant.datahealth); nothing is cached here."""

from __future__ import annotations

import sys
from dataclasses import asdict

from pages import ROOT

if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))


def rows() -> list[dict]:
    from quant import datahealth

    return [asdict(h) for h in datahealth.report()]


def render(mo, filters: dict):
    try:
        data = rows()
    except Exception as e:  # noqa: BLE001 - show the reason instead of a traceback
        return mo.callout(
            mo.md(
                f"Could not read the bucket: `{str(e).splitlines()[0]}`. Check `.env` (`just onboard`)."
            ),
            kind="warn",
        )
    if not data:
        return mo.md("_No dataset READMEs under catalog/datasets/._")
    stale = [r for r in data if r["status"] != "ok"]
    head = mo.md(f"**{len(data)} dataset(s)**, {len(stale)} not ok. Fix with `just refresh`.")
    return mo.vstack([head, mo.ui.table(data, selection=None)])
