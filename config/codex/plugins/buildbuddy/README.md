# BuildBuddy Plugin

This plugin groups public BuildBuddy workflows that are safe to track in
dotfiles:

- invocation troubleshooting and artifact lookup
- invocation comparison and cache-miss analysis
- remote action replay command generation
- usage and billing trend analysis

BuildBuddy also exposes an official MCP server at
`https://<your-org>.buildbuddy.io/mcp`. Treat it as an optional convenience
surface, not a replacement for the bundled API-backed skills, since it currently
exposes fewer APIs. See `references/buildbuddy-mcp.md` for the local
configuration shape.

Keep development-only, internal, admin, or impersonation-token workflows out of
this plugin. Those belong in the local-only `buildbuddy-dev` plugin.
