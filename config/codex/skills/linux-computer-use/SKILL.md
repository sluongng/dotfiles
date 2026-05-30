---
name: linux-computer-use
description: Use the local linux-computer-use CLI or MCP server to inspect and safely interact with visible Hyprland desktop apps through screenshots, AT-SPI state, app approvals, dry-run raw input, and MCP-compatible Computer Use tool calls.
---

# Linux Computer Use

Use this skill when a task needs local desktop state or a controlled desktop action on this Hyprland machine.

## Start

Verify the installed command first:

```bash
command -v linux-computer-use
linux-computer-use --json doctor
```

`doctor` is expected to report no auth requirement. Treat missing `grim`, missing AT-SPI, inactive `ydotoold`, missing `/dev/uinput` access, or absent Hyprland as capability limits, not as reasons to guess.

## Read Path

List and resolve windows before capturing state:

```bash
linux-computer-use --json apps list --limit 20
linux-computer-use --json apps resolve active
linux-computer-use --json state get --app active --out /tmp/linux-computer-use-state
```

Use app queries accepted by the CLI: `active`, `hypr:<address>`, `pid:<pid>`, `class:<exact-class>`, `title:<substring>`, or a string that `apps resolve` can match.

Prefer `state get` before element-targeted actions. It stores a state id and element ids that can be reused by the CLI or MCP tools.

## Action Path

Raw input uses `wtype` or `ydotool`, and requires an app approval unless `--dry-run` is set. Always dry-run first for raw keyboard, pointer, scroll, or drag actions:

```bash
linux-computer-use --json --dry-run action press-key --app active --key ctrl+l
linux-computer-use --json approvals grant --app active --scope session
linux-computer-use --json action type-text --app active --text "hello"
```

Element actions should use AT-SPI first when possible:

```bash
linux-computer-use --json action click --app active --state-id <state_id> --element <element_id>
linux-computer-use --json action set-value --app active --state-id <state_id> --element <element_id> --value "text"
linux-computer-use --json action secondary --app active --state-id <state_id> --element <element_id> --action <name>
```

Do not run live write actions against Slack, Chrome, Discord, terminals, browsers, or externally visible apps unless the user explicitly approved that exact target and action. Use a controlled test window for manual write checks.

## Raw Escape Hatch

Call MCP-style tools directly from the shell when that is easier than starting the MCP server:

```bash
linux-computer-use --json tool-call list_apps --args-json '{"limit":10}'
linux-computer-use --json tool-call get_app_state --args-json '{"app":"active"}'
linux-computer-use --json --dry-run tool-call type_text --args-json '{"app":"active","text":"hello"}'
```

For Codex MCP integration, configure:

```toml
[mcp_servers.linux-computer-use]
command = "linux-computer-use"
args = ["mcp"]
startup_timeout_sec = 10
```
