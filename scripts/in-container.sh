#!/bin/sh
# Run one command in the devcontainer from the host, for an assistant (Claude Code, Codex) that runs
# outside it: `sh scripts/in-container.sh just check`. Uses the devcontainer CLI when it is
# installed; otherwise docker run on an image built from .devcontainer/Dockerfile (built on first
# use), with the same volumes as devcontainer.json, .env passed as environment, and the host's git
# identity so commits made in the container pass the pre-commit hooks.
set -e
root=$(cd "$(dirname "$0")/.." && (pwd -W 2>/dev/null || pwd))
if command -v devcontainer >/dev/null 2>&1; then
  exec devcontainer exec --workspace-folder "$root" "$@"
fi
image=semi-sys-dev
docker image inspect "$image" >/dev/null 2>&1 || docker build -t "$image" -f "$root/.devcontainer/Dockerfile" "$root"
envfile=""
[ -f "$root/.env" ] && envfile="--env-file=$root/.env"
export MSYS_NO_PATHCONV=1
# shellcheck disable=SC2086
exec docker run --rm -i $envfile \
  -v "$root:/workspaces/semi-systematic" \
  -v semi-systematic-venv:/opt/venv -v semi-systematic-uv-cache:/root/.cache/uv \
  -w /workspaces/semi-systematic \
  -e GIT_CONFIG_COUNT=1 -e GIT_CONFIG_KEY_0=safe.directory -e GIT_CONFIG_VALUE_0='*' \
  -e GIT_AUTHOR_NAME="$(git -C "$root" config user.name)" -e GIT_AUTHOR_EMAIL="$(git -C "$root" config user.email)" \
  -e GIT_COMMITTER_NAME="$(git -C "$root" config user.name)" -e GIT_COMMITTER_EMAIL="$(git -C "$root" config user.email)" \
  "$image" "$@"
