---
name: chrome-devtools
description: Inspect, instrument, and control a local Google Chrome through the Chrome DevTools MCP server. Use when Claude needs live Chrome tabs, navigation, DOM/console/network inspection, or Chrome DevTools Protocol commands against a running browser, rather than the headless browser automation covered by the playwright skill.
---

# Chrome DevTools

Use the **Chrome DevTools MCP** server as the interface to a running Chrome on
this machine. Its tools surface as `mcp__chrome-devtools__*` (load schemas with
ToolSearch when they are not already in context). They drive Chrome over the
Chrome DevTools Protocol and return structured results.

For scripted, headless, or cross-browser end-to-end automation, prefer the
`playwright` skill instead. Reach for Chrome DevTools MCP when you specifically
need to attach to and inspect the user's live Chrome session.

## Prerequisites

The Chrome DevTools MCP server must be configured for the session. If the
`mcp__chrome-devtools__*` tools are absent:

1. Confirm the server is registered (project or user `.mcp.json` /
   `settings.json`, or `claude mcp list`).
2. The common server is `chrome-devtools-mcp` (`npx chrome-devtools-mcp@latest`),
   which launches or attaches to Chrome and exposes DevTools Protocol tooling.
3. If it cannot be enabled, fall back to the `playwright` skill and say so.

## Workflow

1. Discover the available `mcp__chrome-devtools__*` tools with ToolSearch and
   read their schemas before calling them.
2. Prefer read-only probes first: list pages/tabs, read the current URL/title,
   snapshot the DOM, read console messages, or capture a screenshot.
3. Use navigation and interaction tools (navigate, click, fill, evaluate) only
   when the task requires changing browser state.
4. Use raw CDP / `evaluate` calls for anything the higher-level tools don't
   cover, e.g.:

   ```js
   // via an evaluate-style tool
   document.title
   ```

5. Clean up after browser work: close throwaway tabs you opened, leaving only
   tabs the user needs for handoff.

## Safety

- Do not read cookies, passwords, local storage, or arbitrary Chrome profile
  files.
- Do not run interaction or raw CDP commands against logged-in sites unless the
  user explicitly asks for that browser action.
- Treat the user's live session as theirs: navigate or mutate state only when
  requested, and report exactly what you did.
