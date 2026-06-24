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
then calls the chatgpt.com Aardvark endpoints directly with Authorization
bearer auth and a browser-style User-Agent header. It does not require Chrome,
the Codex Chrome extension, browser cookies, or local storage.

If chatgpt.com returns a perimeter 403, retry with a fresher User-Agent via
`CODEX_SECURITY_CLOUD_USER_AGENT` or `--user-agent`. Do not add cookies or
browser automation unless the user explicitly asks for a separate fallback.

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
2. If doctor with `--probe` returns 403, retry with a current browser
   User-Agent:

       CODEX_SECURITY_CLOUD_USER_AGENT='Mozilla/5.0 ... Chrome/... Safari/537.36' python3 scripts/codex_security_cloud.py doctor --probe

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
