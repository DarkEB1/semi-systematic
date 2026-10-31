# shellcheck shell=bash
# Source this to configure an rclone remote named "r2" from the R2_* variables in .env.
# Used by `just ls` and scripts/backup.sh. Nothing is written to disk.
: "${R2_ACCESS_KEY_ID:?R2_ACCESS_KEY_ID is not set (see .env.example)}"
: "${R2_SECRET_ACCESS_KEY:?R2_SECRET_ACCESS_KEY is not set (see .env.example)}"
: "${R2_ENDPOINT:?R2_ENDPOINT is not set (see .env.example)}"
export RCLONE_CONFIG_R2_TYPE=s3
export RCLONE_CONFIG_R2_PROVIDER=Cloudflare
export RCLONE_CONFIG_R2_ACCESS_KEY_ID="$R2_ACCESS_KEY_ID"
export RCLONE_CONFIG_R2_SECRET_ACCESS_KEY="$R2_SECRET_ACCESS_KEY"
export RCLONE_CONFIG_R2_ENDPOINT="$R2_ENDPOINT"
export RCLONE_CONFIG_R2_REGION=auto
export RCLONE_CONFIG_R2_NO_CHECK_BUCKET=true
