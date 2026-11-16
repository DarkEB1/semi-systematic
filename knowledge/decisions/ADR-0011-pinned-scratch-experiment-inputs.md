---
id: ADR-0011-pinned-scratch-experiment-inputs
type: decision
title: "ADR-0011: allow checksum-pinned scratch inputs before promotion"
date: 2026-11-03
authors: [DarkEB1]
owner: DarkEB1
status: accepted
tags: [data, infra]
related: [data-access, ADR-0001-initial-setup]
---

# ADR-0011: allow checksum-pinned scratch inputs before promotion

## Context

Research must use `quant.data.load(config)`, while newly acquired data stays in scratch pending owner-reviewed promotion. The existing loader could only read curated objects. Running an experiment to decide whether data merit promotion otherwise requires promoting unresearched inputs first or bypassing the loader.

## Decision

Extend each dataset declaration with optional `scratch_key` and mandatory `sha256` when that key is present. Keep the dataset `name` and ISO `snapshot`. A scratch key must name exactly one Parquet object, contain the matching `snapshot=YYYY-MM-DD` directory, and contain no wildcards or traversal. Verify the digest of the serialized object and the existing catalog schema before returning data. No implicit fallback from curated to scratch. Duplicate dataset names fail. Existing curated declarations behave as before.

This supplements the loading convention; it changes no write permissions and does not supersede ADR-0001's storage policy. Research configs distinguish acquisition snapshots from promotion snapshots explicitly. Dataset README, config and manifest must carry provenance. Scratch results remain draft until their retention and promotion are resolved; a checksum detects changes but cannot prevent object expiry.

## Consequences

The data layer can support the requested pre-promotion experiment without raw/curated writes or local-file shortcuts. Tests cover wrong digests, schema drift, key traversal and missing pinning. Data-layer ownership still applies: this change is reviewed in a PR and not self-merged. Expiring scratch objects can make reruns unavailable, so a final long-lived experiment needs owner-approved promotion.

## Alternatives considered

- Read local files or call storage clients from the notebook: bypasses the required loader.
- Write directly to curated: violates the workflow's write policy.
- Promote before exploratory validation: reverses the purpose of scratch.
