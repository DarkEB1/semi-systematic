#!/usr/bin/env python
"""Two caps on tracked or to-be-tracked files: no file over 1 MB (data lives in the bucket, not in
git; catalog/reference/*.csv are small hand-maintained tables) and no python file over 400 lines
(a unit an agent or a person reads in one pass; split by responsibility, ADR-0005)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAP = 1_000_000
LINE_CAP = 400


def main() -> int:
    out = subprocess.run(
        ["git", "ls-files", "-co", "--exclude-standard", "-z"],
        cwd=ROOT,
        capture_output=True,
        check=True,
    ).stdout
    files = [f for f in out.decode("utf-8", "replace").split("\0") if f]
    big, long = [], []
    for f in files:
        p = ROOT / f
        if not p.is_file():
            continue
        if p.stat().st_size > CAP:
            big.append((f, p.stat().st_size))
        if f.endswith(".py") and not f.startswith("research/"):
            lines = p.read_text(encoding="utf-8", errors="replace").count("\n")
            if lines > LINE_CAP:
                long.append((f, lines))
    for f, n in big:
        print(f"{f}: {n / 1e6:.2f} MB exceeds the 1 MB cap (put data in the bucket)")
    for f, n in long:
        print(f"{f}: {n} lines exceeds the {LINE_CAP}-line cap (split by responsibility)")
    print(
        f"size cap: {len(files)} file(s) checked, {len(big)} over 1 MB, {len(long)} over {LINE_CAP} lines"
    )
    return 1 if big or long else 0


if __name__ == "__main__":
    sys.exit(main())
