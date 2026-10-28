---
name: buildbuddy
description: Route BuildBuddy troubleshooting, API selection, and analytics questions to focused skills and shared API references.
---

# BuildBuddy

## Overview

Use this as the umbrella entrypoint for public BuildBuddy workflows. It should
classify the request quickly and route to the most specific bundled skill.

This plugin is for workflows that are safe to keep in dotfiles. Local
development, internal operations, direct metrics access, database queries, and
log lookup workflows belong in the local-only `buildbuddy-dev` plugin instead.

BuildBuddy also has an official MCP server. Use it opportunistically when the
requested operation is exposed by that server, but do not replace the
API-backed workflows below with MCP-only logic; the MCP surface is narrower.
Load `../../references/buildbuddy-mcp.md` when the user asks how to configure
the official MCP server.

## API references

Start with [the API index](../../references/api-reference.md) for API discovery,
request/response source maps, and the public-v1 versus UI-RPC distinction.
Use [common conventions](../../references/api-common.md) for auth and JSON, then
load only the linked request examples needed for the task.
Workflow procedures stay with their skills; do not load every reference.

## Routing

Route by user intent:

- Invocation failure, target logs, execution details, profiles, raw BES, or
  cache scorecard: `../buildbuddy-invocation-troubleshoot/SKILL.md`
- Two invocation URLs or IDs, cache invalidation, hermeticity, first shared AC
  miss, or Action/ActionResult diffs:
  `../buildbuddy-invocation-compare/SKILL.md`
- Replaying one remote action, modifying action args/env/exec properties, or
  pinning to an executor: `../buildbuddy-action-reproduce/SKILL.md`
- Recent flaky tests, Test Analytics flakes lists, target flake samples, or
  recurring flaky-test triage: `../buildbuddy-flaky-tests/SKILL.md`
- Pasted BuildBuddy or `bb` CLI log snippets, customer symptoms, FastCDC
  warnings, BES upload failures, confusing invocation IDs, or source-backed
  root-cause questions without a clean invocation URL:
  `../buildbuddy-log-root-cause/SKILL.md`
- Source-backed questions spanning Bazel client behavior, BuildBuddy server,
  executor or toolchain images, Helm chart settings, Bazelisk versions,
  regressions, or large-repo history across `bazelbuild/bazel`,
  `buildbuddy-io/buildbuddy`, `buildbuddy-io/buildbuddy-toolchains`, and
  `buildbuddy-io/buildbuddy-helm`:
  `../ask-buddy/SKILL.md`
- Billing, usage, Target Performance, cross-invocation action timelines, trends,
  heatmaps, drilldowns, cost anomalies, or projections:
  `../buildbuddy-usage-analysis/SKILL.md`

## Safety

- Check API key presence without printing the key.
- Store downloaded API responses and artifacts in a temp directory.
- Keep time windows narrow unless the user asks for a larger analysis.
- Redact credentials and private URLs before sharing output.
