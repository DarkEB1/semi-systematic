# The only interface people, agents and CI use. Scripts, skills and workflows call
# these recipes, never raw commands. Run `just` to list them.

set dotenv-load := true
set positional-arguments := true
set shell := ["bash", "-euo", "pipefail", "-c"]

default:
    @just --list --unsorted

# --- environment ---------------------------------------------------------------

# Install hooks and sync the locked environment (run once per container)
setup:
    uv sync --frozen --all-groups --all-extras
    uv run pre-commit install --install-hooks

# Verify this machine and .env, and print what is missing
onboard:
    uv run python scripts/onboard.py

# --- quality gates -------------------------------------------------------------

# Run the test suite
test:
    uv run pytest

# Lint, frontmatter, links, size cap, env-var audit, frozen experiments, secrets
check:
    uv run ruff check .
    uv run ruff format --check .
    uv run python scripts/check_frontmatter.py
    uv run python scripts/check_links.py
    uv run python scripts/check_size.py
    uv run python scripts/check_env.py
    uv run python scripts/check_frozen.py
    gitleaks dir . --redact --no-banner --exit-code 1

# Diff every skill's deterministic part against its golden fixture (ai/evals)
eval *ARGS:
    uv run python scripts/run_evals.py "$@"

# --- data ----------------------------------------------------------------------

# Ingest one registered source: just ingest SOURCE [--since YYYY-MM-DD]
ingest SOURCE *ARGS:
    uv run python -m quant.ingest "$1" "${@:2}"

# Find gaps between expected and actual raw partitions and re-ingest them
refresh *ARGS:
    uv run python .claude/skills/refresh-data/run.py "$@"

# Execute a promote request (CI): just promote promote/requests/<file>.yml
promote REQUEST:
    uv run python -m quant.promote "$1"

# Validate a scratch Parquet against its dataset README and write a promote request
promote-request NAME SCRATCH_KEY *ARGS:
    uv run python .claude/skills/promote-dataset/run.py "$1" "$2" "${@:3}"

# Scaffold an ingest module, README, catalog view, test and workflow entry for SOURCE
scaffold-source SOURCE *ARGS:
    uv run python .claude/skills/pull-data/run.py "$1" "${@:2}"

# Latest partition vs expected cadence for every raw dataset (headless data-health page)
data-health *ARGS:
    uv run python -m quant.datahealth "$@"

# List the bucket and flag keys outside raw/, curated/, scratch/<handle>/ or size > 8 GB
audit *ARGS:
    uv run python -m quant.audit "$@"

# List objects under a bucket prefix with rclone: just ls scratch/
ls PREFIX="":
    source scripts/rclone_env.sh && rclone ls "r2:${R2_BUCKET}/$1"

# Sync raw/ and curated/ to the B2 backup bucket (skips with a notice until B2 is configured)
backup:
    bash scripts/backup.sh

# --- knowledge and retrieval ---------------------------------------------------

# Rebuild .index/chunks.parquet and regenerate knowledge/INDEX.md
index:
    uv run brain build
    uv run brain index-md

# Search the repo index: just search "R2 bucket"
search QUERY:
    uv run brain search "$1"

# Embed chunks (errors until EMBEDDING_MODEL is configured)
embed:
    uv run brain embed

# Print the controlled tag vocabulary from knowledge/context/tags.md
tags:
    uv run python scripts/tags.py

# Scaffold a meeting file from the template: just meeting 2026-10-29 "weekly sync"
meeting DATE TITLE *ARGS:
    uv run python .claude/skills/meeting-notes/run.py "$1" "$2" "${@:3}"

# Explain where a new thing goes and check convention files agree: just where "ingest module"
where THING:
    uv run python .claude/skills/repo-structure/run.py "$1"

# --- research ------------------------------------------------------------------

# Create research/experiments/<today>-<slug>/ (or --finish to draft results and the log entry)
experiment SLUG *ARGS:
    uv run python .claude/skills/new-experiment/run.py "$1" "${@:2}"

# Run the internal dashboard hub (marimo) on port 2718
dashboard *ARGS:
    uv run marimo run dashboards/hub/app.py --host 0.0.0.0 --port 2718 --headless "$@"

# --- agents --------------------------------------------------------------------

# Create ai/tasks/<slug>.yaml with a budget, stop conditions and allowed paths
task SLUG *ARGS:
    uv run python scripts/task.py "$1" "${@:2}"

# Re-invoke the task's skill until a stop condition or the budget is hit
loop SLUG *ARGS:
    uv run python scripts/loop.py "$1" "${@:2}"
