# semi-systematic

This repository is the data, research, and dashboard for the project. It is the systematic side, organised as a monorepo.

## Description

Markets are an aggregate picture of the mapping of price to value. Most of society's problems are solved if this mapping is entirely representative. So if we want our engagements in the market to be productive, they should reflect our value judgements.

This fund is aimed at expressing these judgements and views efficiently.

There are broadly two players in the market: the cogs, and the oil. The cogs express views, they take prices, and they present an outlook. The oil sits in-between them to ensure all works as intended without too much inefficiency and mispricing.

The aim with this is to combine both perspectives on the market. We want to use quantitative signals, models, and constructs to give us a representative picture of what expectations are encoded into market prices. We then want to see where these expectations differ from our own value judgements and bet on these discrepancies in a rigorously defined manner.

We essentially want the systematic side to give us a clear idea of the aggregate opinion and how it propagates across assets in a way that allows us to express our opinions where they yield the most favorably asymmetric distribution of returns. The models anchor our way of looking at and across markets.

Our goal is to learn from each other's perspectives in discussion, learn how to build defensible value judgements, learn how to base these in models that we build, and learn how to build these views of the market from first principles and resourcefully. We want to build a view, not learn a view.

## Markets

The markets we focus on are preliminarily EM and FX, restricted by the data available for us to form opinions.

## What is in here

Everything the team knows and builds lives here as plain text with consistent metadata: notes,
meeting minutes and decisions under `knowledge/`, experiments and signals under `research/`, the
data layer and catalog under `src/quant/` and `catalog/`, one dashboard hub under `dashboards/`,
and the skills AI agents run under `.claude/skills/`. A retrieval index is built over all of it
(`just search "..."`). Data itself lives in a Cloudflare R2 bucket, never in git.

Start with [knowledge/context/start-here.md](knowledge/context/start-here.md): the reading
order, the annotated tree, what a week leaves behind, and a first hour for people and one for
agents. From there: [AGENTS.md](AGENTS.md) (map, nine rules, skills, `just` interface),
[workflow.md](knowledge/context/workflow.md) (the story of a week),
[walkthrough.md](knowledge/context/walkthrough.md) (the same week as real commands and output),
[data-access.md](knowledge/context/data-access.md) (reading and writing data),
[working-with-agents.md](knowledge/context/working-with-agents.md) (invoking skills, loops,
reviewing agent PRs) and [CONTRIBUTING.md](CONTRIBUTING.md) (branches, PRs, CI, conventions).
The devcontainer is the only supported way to run anything here, by people or agents.

## Set up by hand

1. Install git, Docker Desktop (or Podman), and VS Code with the Dev Containers extension (or Claude Code).
2. Clone `github.com/DarkEB1/semi-systematic` and open it in the devcontainer (VS Code: "Reopen in
   Container"; CLI: `devcontainer up --workspace-folder .`). `just setup` runs automatically.
3. `cp .env.example .env` and fill it from the team password manager: the shared R2 account id,
   endpoint and bucket; your `team-read` key pair; your `<handle>-scratch` key pair; your handle.
4. `just onboard` prints a checklist of what is missing. Then `just check` and `just test`.
5. Register yourself in one PR: `knowledge/notes/<handle>/.gitkeep`, your handle in
   `knowledge/context/team.yaml`, and a `/knowledge/notes/<handle>/ @<handle>` line in `.github/CODEOWNERS`.

## Set up with your AI assistant

Paste the block below into Claude, ChatGPT or any assistant that has a terminal on your machine.

```text
You are helping me set up a development machine for the repository github.com/DarkEB1/semi-systematic,
a quant research monorepo. You have not seen this repo before. Work step by step, run the commands
yourself where you have a terminal, and show me each command's output before moving on. Rules for the
whole session: never ask me to paste a password, key or token into this chat; never read a secret value
back to me, print it, log it, or commit it; when a value is needed in a file, open the file for me and
tell me which line to fill, then continue when I say "done".

STEP 1: prerequisites. Detect my OS. Check each tool with a version command, install what is missing,
then check again:
- git (`git --version`). macOS: `xcode-select --install` or Homebrew; Windows: winget install Git.Git;
  Linux: the distro package.
- Docker Desktop (`docker --version` and `docker info` must both work; Docker Desktop must be running).
  Podman with `podman machine` is an acceptable substitute; then install the devcontainer CLI too.
- Either VS Code (`code --version`) with the "Dev Containers" extension
  (`code --install-extension ms-vscode-remote.remote-containers`), or Claude Code (`claude --version`),
  plus the devcontainer CLI (`npm install -g @devcontainers/cli`, check `devcontainer --version`).

STEP 2: clone and open in the devcontainer. `git clone https://github.com/DarkEB1/semi-systematic.git`,
`cd semi-systematic`. If using VS Code: `code .` then run "Dev Containers: Reopen in Container". If using
the CLI: `devcontainer up --workspace-folder .` and then run every later command as
`devcontainer exec --workspace-folder . <command>`. The container build installs Python, uv, just, rclone,
duckdb, gitleaks and gh and then runs `just setup` (dependency sync and pre-commit hooks); wait for it to
finish (a few minutes the first time). Everything below runs INSIDE the container.

STEP 3: create .env. Run `cp .env.example .env`, then open .env in my editor. For each variable, tell me
what it is and where I get it, wait for me to fill it, and never ask me to paste it to you:
- R2_ACCOUNT_ID, R2_ENDPOINT, R2_BUCKET: shared, non-secret. In the team password manager under
  "R2 shared". The bucket is in the EU jurisdiction so the endpoint looks like
  https://<account-id>.eu.r2.cloudflarestorage.com and the bucket is semi-sys-research-data.
- R2_ACCESS_KEY_ID and R2_SECRET_ACCESS_KEY: my read key. Password manager entry "team-read".
- R2_HANDLE: my GitHub handle exactly as spelled on GitHub.
- R2_SCRATCH_ACCESS_KEY_ID and R2_SCRATCH_SECRET_ACCESS_KEY: my personal write key. Password manager
  entry "<my handle>-scratch". If no such entry exists, tell me to ask the data-layer owner (DarkEB1) to
  create an R2 token named "<handle>-scratch" (Object Read & Write on the one bucket) and leave these
  two lines empty for now.
- Everything else in .env.example (QUANT_ROLE, VENDOR_API_KEY, B2_*, EMBEDDING_MODEL, GH_TOKEN) stays
  empty on a laptop.
Confirm the file is saved. Do not cat it.

STEP 4: verify. Run, in order, and fix failures before going on:
- `just onboard` prints a checklist; every line must be OK except the scratch key lines, which may be WARN.
- `just check` (lint, frontmatter, links, size cap, env audit, frozen experiments, secret scan).
- `just test`.
- `just search "setup"` must print at least one hit (it builds the index on first use).
- `just ls` must list the bucket without error (it may print nothing if the bucket is empty).
Common failures and fixes: "Cannot connect to the Docker daemon" means Docker Desktop is not running,
start it and retry; a MISSING line for an R2_ variable means .env is incomplete, go back to STEP 3;
"SignatureDoesNotMatch", "InvalidAccessKeyId" or a 403 means a key was pasted with a stray space or the
endpoint is wrong (it must contain the account id and ".eu."); "uv: command not found" or
"just: command not found" means you are running outside the container, go back to STEP 2.

STEP 5: register me. Inside the container: create knowledge/notes/<handle>/.gitkeep if missing; add
<handle> to the handles list in knowledge/context/team.yaml; add the line
"/knowledge/notes/<handle>/ @<handle>" to .github/CODEOWNERS. Then `git checkout -b chore/onboard-<handle>`,
`git add -A`, `git commit -m "chore: onboard <handle>"`, `git push -u origin HEAD`, and
`gh pr create --fill` (run `gh auth login` first if it asks; follow its browser flow, I will do the
login myself). Show me the PR URL.

STEP 6: finish. Run `just onboard` once more and show me the output. Then tell me to read AGENTS.md
and knowledge/context/workflow.md next, and stop.
```

`just onboard` is the one command both you and the assistant can use to check where you stand.
