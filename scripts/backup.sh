#!/usr/bin/env bash
# Weekly backup: rclone sync of raw/ and curated/ from R2 to a Backblaze B2 bucket.
# B2 keeps versions itself (bucket lifecycle "keep all versions"), so a bad sync is recoverable.
# Skips with a notice until B2_KEY_ID, B2_APPLICATION_KEY and B2_BUCKET exist (see ADR-0001 TODO).
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ -z "${B2_KEY_ID:-}" || -z "${B2_APPLICATION_KEY:-}" || -z "${B2_BUCKET:-}" ]]; then
  echo "backup: B2 is not configured (B2_KEY_ID / B2_APPLICATION_KEY / B2_BUCKET empty); skipping. See ADR-0001."
  exit 0
fi

# shellcheck source=scripts/rclone_env.sh
source scripts/rclone_env.sh
export RCLONE_CONFIG_B2_TYPE=b2
export RCLONE_CONFIG_B2_ACCOUNT="$B2_KEY_ID"
export RCLONE_CONFIG_B2_KEY="$B2_APPLICATION_KEY"

for prefix in raw curated; do
  echo "backup: syncing ${prefix}/ -> b2:${B2_BUCKET}/${prefix}/"
  rclone sync "r2:${R2_BUCKET}/${prefix}" "b2:${B2_BUCKET}/${prefix}" --fast-list --transfers 8 --stats-one-line -v
done
echo "backup: done"
