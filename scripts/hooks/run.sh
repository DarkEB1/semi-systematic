#!/bin/sh
# Run a hook script from scripts/hooks/ with whatever python the host has. Claude Code hooks run on
# the machine where Claude Code runs, not in the devcontainer, so this never assumes uv or ruff.
# Usage: run.sh <script.py> [args...]; the hook JSON arrives on stdin and is passed through unchanged.
dir=$(cd "$(dirname "$0")" && pwd)
script=$1
shift
if command -v python3 >/dev/null 2>&1; then
  exec python3 -I "$dir/$script" "$@"
elif command -v python >/dev/null 2>&1; then
  exec python -I "$dir/$script" "$@"
fi
echo "hooks: no python on this machine; $script skipped" >&2
exit 0
