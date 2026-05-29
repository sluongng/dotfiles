# Official BuildBuddy MCP Server

BuildBuddy exposes an official Streamable HTTP MCP server at:

```text
https://<your-org>.buildbuddy.io/mcp
```

Configure it with a local environment variable for the API key. Do not write the
API key value into dotfiles or plugin files.

Example `~/.codex/config.local.toml` snippet:

```toml
[mcp_servers.buildbuddy]
url = "https://<your-org>.buildbuddy.io/mcp"
bearer_token_env_var = "BUILDBUDDY_API_KEY"
```

Codex reads `bearer_token_env_var` and sends it as:

```text
Authorization: Bearer <token>
```

Use the MCP server for supported quick tool calls. Prefer the bundled
BuildBuddyService-backed skills when you need APIs not exposed by MCP, such as
deeper invocation troubleshooting, execution/action comparison, replay command
generation, or usage drilldowns.
