---
name: codex-security-cloud
description: Use when the user wants to list, inspect, or import ChatGPT-hosted Codex Security Cloud or Aardvark scan findings and accessible repos using local Codex ChatGPT credentials.
---

# Codex Security Cloud

Use this skill to access the ChatGPT-hosted Codex Security Cloud findings UI
data from a local Codex session.

## Scope

This skill is an intake and query workflow. It does not discover new findings,
triage security impact, validate exploitability, or fix code. Hand findings to
the Codex Security skills for those later phases.

## Auth Model

The cloud findings API uses the ChatGPT web access token that Codex stores for
auth_mode chatgpt. It is not authenticated by OPENAI_API_KEY.

The helper reads the token from CODEX_ACCESS_TOKEN or from ~/.codex/auth.json,
then runs the API call inside a chatgpt.com Chrome page context through
codex-linux-extension-host. This satisfies the browser perimeter while sending
only an Authorization bearer header.

Do not print access tokens, refresh tokens, cookies, or local storage.

## Commands

Run commands from the plugin root:

    python3 scripts/codex_security_cloud.py doctor
    python3 scripts/codex_security_cloud.py list-repos
    python3 scripts/codex_security_cloud.py list-findings --repo buildbuddy-io/buildbuddy --limit 20
    python3 scripts/codex_security_cloud.py get-finding 3e3cd14d62e08191a5af5494d13a30b1

For machine-readable output:

    python3 scripts/codex_security_cloud.py list-findings --repo buildbuddy-io/buildbuddy --format json

## Workflow

1. Run doctor first when access has not been checked in the current session.
2. If Chrome access fails, open https://chatgpt.com/codex/cloud/security/findings
   in the Codex Chrome profile and sign in, then retry.
3. Use list-repos to discover accessible repositories when the repo is unknown.
4. Use list-findings for the paginated queue. The list response contains
   lightweight items; finding titles are under commit_analysis.title.
5. Use get-finding with a hid for full details such as validation report, attack
   path analysis, proposed patch metadata, and relevant lines.

## API Notes

Observed same-origin endpoints:

    GET /backend-api/aardvark/scan-findings
    GET /backend-api/aardvark/scan-findings/{finding_id}
    GET /backend-api/aardvark/scan-findings/list-accessible-repos
    GET /backend-api/aardvark/scan-findings/list-authors
    GET /backend-api/aardvark/scan_configurations

The 32-character IDs in the findings page URL are Aardvark finding hid values,
not Codex Security MCP UUID scanId values.

## Output Hygiene

When summarizing to the user:

- Include endpoint status and result counts.
- Include finding titles, repos, criticality, status, commit hash, and hid.
- Do not include bearer tokens, cookies, refresh tokens, or raw browser storage.
- If a request fails, report the HTTP status and non-secret error string only.
