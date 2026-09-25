# Codex config

This directory only tracks non-sensitive Codex configuration that should be shared
via dotfiles.

Deploy it with:

```sh
./automation/codex/install-codex.sh
```

The deploy script manages these paths under `${CODEX_HOME:-~/.codex}`:

- preserves App-managed desktop, hook trust, bundled plugin, `node_repl`, and
  trusted Browser shell-environment tables in `runtime.local.toml`, then renders
  `config.toml` from the tracked shared config plus local overlays
- preserves the live TUI `session_picker_view` preference and
  `screen_reader_detection_done` marker through the same runtime overlay;
  other TUI settings remain controlled by the shared config
- tracked global `AGENTS.md`
- tracked files under `agents/`
- tracked `profiles/*.config.toml` as named profile files beside `config.toml`
- tracked custom skill directories under `skills/`
- tracked local plugins under `plugins/`, synced into Codex's plugin cache by
  plugin manifest name and version

Tracked plugin marketplaces can live in this directory as:

- `.agents/plugins/marketplace.json`
- `plugins/<plugin-name>/`

Enable those marketplaces from `${CODEX_HOME:-~/.codex}/config.local.toml`
with a local absolute `source` path. Keep development-only plugins under
`${CODEX_HOME:-~/.codex}/local` so they stay outside dotfiles git.

Keep desired `[plugins."<name>@<marketplace>"]` enabled state for tracked
personal plugins in `config.toml`. The marketplace location is machine-local,
but the desired plugin state must be part of the rendered source of truth so a
later deploy does not silently discard an install made by `codex plugin add`.

The deploy script materializes tracked local marketplace plugins into
`${CODEX_HOME:-~/.codex}/plugins/cache` by plugin manifest name and version.
Bump the plugin manifest version when changing tracked plugin contents so fresh
Codex sessions pick up the new cache entry, or clear the matching cache entry
to force a local refresh.

The rendered config is platform-aware:

- forked-zsh backends stay disabled on both macOS and Linux because the CLI and
  Desktop share config but may ship different resource layouts;
- it probes whether the installed CLI accepts nested feature configuration and
  emits the compatible legacy boolean form for older Codex releases;
- it probes experimental context-management support separately; set
  `CODEX_CONTEXT_MANAGEMENT_TABLE=false` when sharing config with an older App;
- it disables the Linux Chrome Bridge-only `chatgpt-threads` plugin on macOS;
- it generates the tracked marketplace source from this checkout when a
  machine-local marketplace entry is not already present;
- redundant local plugin tables that exactly match tracked desired state are
  ignored, while conflicting overrides fail before replacing the live config.

It intentionally leaves `auth.json`, histories, logs, memories, SQLite state,
and Codex-managed system skills as local machine state inside the selected
Codex home.

Do not edit the rendered `config.toml` directly. Update the tracked shared
config in this directory, or use one of these machine-local files instead:

- `${CODEX_HOME:-~/.codex}/config.local.toml` for additive local-only settings
- `${CODEX_HOME:-~/.codex}/projects.local.toml` for local trust entries (`[projects]`)
- `${CODEX_HOME:-~/.codex}/runtime.local.toml` for App-managed desktop, hook
  trust, bundled plugin, `node_repl`, and trusted Browser shell-environment
  state, plus the two UI-owned TUI values above; the deploy script updates this
  file from the live config automatically

These files live outside the checkout. The matching `*.local.toml` names are
also ignored under this directory so a copied local overlay cannot be added by
mistake. The repository hooks reject active or commented `[projects]` tables
in every outgoing revision of the shared config.

Run `init.sh` after a direct clone or pull to activate the tracked hooks, or
configure them explicitly with:

```sh
git config core.hooksPath .githooks
```

Do not commit secrets, API keys, or machine-local project paths here.

## Delegation

The interactive default is Astra/high. Up to six spawned agents can be open
concurrently, excluding the parent; maximum depth remains two. The role list is
larger than the concurrency budget so the parent can select the right mix.

| Role | Model / reasoning | Assignment |
| --- | --- | --- |
| `scout` | GPT-6 Luna / high | Narrow read-only evidence gathering |
| `worker` | GPT-6 Sol / medium | Well-specified implementation |
| `quick-worker` | Astra / low | Small decided edits with multiple constraints |
| `advanced-worker` | Astra / medium | Bounded implementation needing design judgment |
| `investigator` | Astra / high | Read-only diagnosis and difficult design analysis |
| `reviewer` | GPT-6 Sol / high | Ordinary independent change review |
| `deep-reviewer` | Astra / high | Security, concurrency, compatibility, and complex review |
| `agy-consult` | Inherited Codex model / medium, advisory CLI workflow | External scout with local evidence verification |

Global `AGENTS.md` supplies routing and ownership guidance. The limit is a
ceiling: useful independent work determines how many agents to spawn. Role
files are installed as regular files; fresh sessions load the current options.
Terra is no longer used by any role or profile.
