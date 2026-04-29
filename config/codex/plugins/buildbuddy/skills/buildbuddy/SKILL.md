---
name: buildbuddy
description: Route public BuildBuddy troubleshooting, invocation comparison, action reproduction, and usage-analysis requests to the focused BuildBuddy skills bundled in this plugin.
---

# BuildBuddy

## Overview

Use this as the umbrella entrypoint for public BuildBuddy workflows. It should
classify the request quickly and route to the most specific bundled skill.

This plugin is for workflows that are safe to keep in dotfiles. Local
development, internal operations, admin impersonation, direct metrics access,
database queries, and log lookup workflows belong in the local-only
`buildbuddy-dev` plugin instead.

BuildBuddy also has an official MCP server. Use it opportunistically when the
requested operation is exposed by that server, but do not replace the
API-backed workflows below with MCP-only logic; the MCP surface is narrower.
Load `../../references/buildbuddy-mcp.md` when the user asks how to configure
the official MCP server.

## Routing

Route by user intent:

- Invocation failure, target logs, execution details, profiles, raw BES, or
  cache scorecard: `../buildbuddy-invocation-troubleshoot/SKILL.md`
- Two invocation URLs or IDs, cache invalidation, hermeticity, first shared AC
  miss, or Action/ActionResult diffs:
  `../buildbuddy-invocation-compare/SKILL.md`
- Replaying one remote action, modifying action args/env/exec properties, or
  pinning to an executor: `../buildbuddy-action-reproduce/SKILL.md`
- Billing, usage, trends, heatmaps, drilldowns, cost anomalies, or projections:
  `../buildbuddy-usage-analysis/SKILL.md`

## Safety

- Check API key presence without printing the key.
- Store downloaded API responses and artifacts in a temp directory.
- Keep time windows narrow unless the user asks for a larger analysis.
- Redact credentials, impersonation headers, and private URLs before sharing
  output.
