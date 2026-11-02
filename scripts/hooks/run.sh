#!/bin/sh
# Run a hook script from scripts/hooks/ with whatever python the host has. Claude Code hooks run on
# the machine where Claude Code runs, not in the devcontainer, so this never assumes uv or ruff.
# Usage: run.sh <script.py> [args...]; the hook JSON arrives on stdin and is passed through unchanged.
# Fails closed: exit 2 (block, reason on stderr) when no python runs or the script crashes, because
# any other exit code lets the action through and a zero-exception rule would be skipped silently.
dir=$(cd "$(dirname "$0")" && pwd)
script=$1
shift
# Try each name by running it: on Windows, python3 can be a Microsoft Store stub that only prints a hint.
for py in python3 python; do
  if "$py" -c "" >/dev/null 2>&1; then
    "$py" -I "$dir/$script" "$@"
    status=$?
    if [ "$status" -eq 0 ] || [ "$status" -eq 2 ]; then
      exit "$status"
    fi
    echo "hooks: $script failed with exit $status; blocking rather than skipping the rule silently" >&2
    exit 2
  fi
done
echo "hooks: no working python on this machine (a Microsoft Store python3 alias does not count); install Python 3 so $script can run. Blocking until then." >&2
exit 2
