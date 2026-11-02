#!/bin/sh
# Run a hook script from scripts/hooks/ with whatever python the host has. Claude Code hooks run on
# the machine where Claude Code runs, not in the devcontainer, so this never assumes uv or ruff.
# Usage: run.sh <script.py> [args...]; the hook JSON arrives on stdin and is passed through unchanged.
dir=$(cd "$(dirname "$0")" && pwd)
script=$1
shift
# Try each name by running it: on Windows, python3 can be a Microsoft Store stub that only prints a hint.
for py in python3 python; do
  if "$py" -c "" >/dev/null 2>&1; then
    exec "$py" -I "$dir/$script" "$@"
  fi
done
echo "hooks: no python on this machine; $script skipped" >&2
exit 0
