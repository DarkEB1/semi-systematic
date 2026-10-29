#!/usr/bin/env python
"""No tracked or to-be-tracked file may exceed 1 MB. Data lives in the bucket, not in git;
catalog/reference/*.csv are small hand-maintained tables."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAP = 1_000_000


def main() -> int:
    out = subprocess.run(
        ["git", "ls-files", "-co", "--exclude-standard", "-z"],
        cwd=ROOT,
        capture_output=True,
        check=True,
    ).stdout
    files = [f for f in out.decode("utf-8", "replace").split("\0") if f]
    big = []
    for f in files:
        p = ROOT / f
        if p.is_file() and p.stat().st_size > CAP:
            big.append((f, p.stat().st_size))
    for f, n in big:
        print(f"{f}: {n / 1e6:.2f} MB exceeds the 1 MB cap (put data in the bucket)")
    print(f"size cap: {len(files)} file(s) checked, {len(big)} over 1 MB")
    return 1 if big else 0


if __name__ == "__main__":
    sys.exit(main())
