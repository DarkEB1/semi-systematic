# The only supported runtime for this repo, for people and agents alike.
# Every tool version is pinned here. Dependabot (docker ecosystem) proposes base-image bumps.
FROM python:3.12.16-slim-bookworm

ARG UV_VERSION=0.13.6
ARG JUST_VERSION=1.59.0
ARG RCLONE_VERSION=1.75.2
ARG DUCKDB_VERSION=2.0.0
ARG GITLEAKS_VERSION=8.30.1
ARG GH_VERSION=2.103.3

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH=/opt/venv/bin:$PATH

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash ca-certificates curl git jq openssh-client unzip \
    && rm -rf /var/lib/apt/lists/*

# uv (pinned via the official distroless image; keep in sync with UV_VERSION)
COPY --from=ghcr.io/astral-sh/uv:0.13.6 /uv /uvx /usr/local/bin/

# just, rclone, duckdb CLI, gitleaks, gh: pinned release binaries
RUN set -eux; \
    arch="$(dpkg --print-architecture)"; \
    case "$arch" in \
      amd64) just_arch=x86_64-unknown-linux-musl;  rclone_arch=amd64; duckdb_arch=amd64; gl_arch=x64;   gh_arch=amd64 ;; \
      arm64) just_arch=aarch64-unknown-linux-musl; rclone_arch=arm64; duckdb_arch=arm64; gl_arch=arm64; gh_arch=arm64 ;; \
      *) echo "unsupported arch $arch"; exit 1 ;; \
    esac; \
    curl -fsSL "https://github.com/casey/just/releases/download/${JUST_VERSION}/just-${JUST_VERSION}-${just_arch}.tar.gz" \
      | tar -xz -C /usr/local/bin just; \
    curl -fsSL -o /tmp/rclone.zip "https://downloads.rclone.org/v${RCLONE_VERSION}/rclone-v${RCLONE_VERSION}-linux-${rclone_arch}.zip" \
      && unzip -q -j /tmp/rclone.zip "*/rclone" -d /usr/local/bin && rm /tmp/rclone.zip; \
    curl -fsSL "https://github.com/duckdb/duckdb/releases/download/v${DUCKDB_VERSION}/duckdb-cli-linux-${duckdb_arch}.tar.gz" \
      | tar -xz -C /usr/local/bin duckdb; \
    curl -fsSL "https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VERSION}/gitleaks_${GITLEAKS_VERSION}_linux_${gl_arch}.tar.gz" \
      | tar -xz -C /usr/local/bin gitleaks; \
    curl -fsSL "https://github.com/cli/cli/releases/download/v${GH_VERSION}/gh_${GH_VERSION}_linux_${gh_arch}.tar.gz" \
      | tar -xz -C /tmp && mv "/tmp/gh_${GH_VERSION}_linux_${gh_arch}/bin/gh" /usr/local/bin/gh && rm -rf /tmp/gh_*; \
    chmod +x /usr/local/bin/just /usr/local/bin/rclone /usr/local/bin/duckdb /usr/local/bin/gitleaks /usr/local/bin/gh; \
    just --version; rclone version | head -1; duckdb --version; gitleaks version; gh --version | head -1

WORKDIR /workspaces/semi-systematic
