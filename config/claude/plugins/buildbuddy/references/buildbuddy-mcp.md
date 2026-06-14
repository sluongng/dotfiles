# Official BuildBuddy MCP Server

BuildBuddy exposes an official Streamable HTTP MCP server at:

```text
https://<your-org>.buildbuddy.io/mcp
```

Configure it with a local environment variable for the API key. Do not write the
API key value into dotfiles or plugin files.

Example `.mcp.json` snippet (project root, or `~/.claude.json` for user scope).
Claude Code expands `${VAR}` from the environment, so the key value stays out of
the file:

```json
{
  "mcpServers": {
    "buildbuddy": {
      "type": "http",
      "url": "https://<your-org>.buildbuddy.io/mcp",
      "headers": {
        "Authorization": "Bearer ${BUILDBUDDY_API_KEY}"
      }
    }
  }
}
```

Equivalently, add it from the CLI:

```sh
claude mcp add --transport http buildbuddy https://<your-org>.buildbuddy.io/mcp \
  --header "Authorization: Bearer ${BUILDBUDDY_API_KEY}"
```

Use the MCP server for supported quick tool calls. Prefer the bundled
BuildBuddyService-backed skills when you need APIs not exposed by MCP, such as
deeper invocation troubleshooting, execution/action comparison, replay command
generation, or usage drilldowns.
