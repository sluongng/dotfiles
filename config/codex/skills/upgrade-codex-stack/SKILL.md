---
name: upgrade-codex-stack
description: "Upgrade or audit the Arch Linux Codex stack: CLI and desktop packages, shared app-server, configuration, and integrations. Use the native updater on other platforms."
---

# Upgrade Codex Stack

This is the Arch Linux workstation upgrade workflow. If `uname -s` is not
`Linux`, stop before using workstation-specific paths, pacman, systemd, or
Linux desktop app steps and use the platform's normal Codex distribution/update
path instead.

For a full upgrade, cover the CLI package, desktop app/runtime, configuration,
plugins, system skills, and services. For an audit or narrower request, inspect
only the relevant components and report current evidence and remaining gaps.

## Scope and Safety

Use these default paths unless the user supplies different ones:

- Codex source and workspace: `$HOME/work/misc/codex`
- Arch package: `$HOME/work/misc/codex/openai-codex-pkg`
- Linux desktop packaging and legacy repackager: `$HOME/work/misc/codex-app`
- Dotfiles source of truth: `$HOME/.dotfiles`
- Live Codex home: `${CODEX_HOME:-$HOME/.codex}`

Before editing:

1. Read every applicable `AGENTS.md` for each repository in scope.
2. Run `git status --short` and inspect relevant existing diffs in every repository.
3. Preserve all pre-existing work and distinguish it from changes made during this run.
4. Use official upstream release metadata, source, documentation, and artifacts as primary evidence.
5. Never print credentials, cookies, tokens, or unredacted authentication payloads.

On this workstation, a request to upgrade the Codex stack authorizes building,
validating, and installing the scoped CLI and existing ChatGPT App packages
through the dedicated root installer without another confirmation. It also
authorizes the necessary runtime restart only after proving that no active
turns or background terminals would be interrupted. Audit-only, build-only,
and narrower requests retain their stated limits.

Use [references/installation.md](references/installation.md) for the exact
privilege check, candidate staging, and installation boundary. Do not infer
missing permission from `sudo -n true`: general sudo access and permission to
start the fixed installer are different. Existing authorization persists; an
idle or validation failure is a technical blocker, not a reason to ask for the
same permission again.

This authorization does not include broadening sudoers, registering package
repositories, running foreign-package maintainer scripts, distribution/profile
migration, or overwriting unrelated live configuration. Preserve explicit
authorization for separately requested configuration changes. If the approved
installation path is unavailable or unsafe, finish preparation and report the
specific blocker and smallest next action; do not silently widen privileges.

The first-party Linux app is the unified ChatGPT desktop app and includes Codex.
Treat its native Linux package and the repository's Arch wrapper for that payload
as the active primary desktop distribution. Do not call it a standalone
Codex-only app. Keep the macOS-derived Linux repackager as an emergency fallback
only; do not retain or reactivate it as a parallel runtime merely because its
files remain on disk. Remove a stale installation only with explicit
authorization after proving that no package, process, open file, desktop entry,
URL handler, profile, or rendered runtime path still uses it. Prefer a
recoverable cleanup such as moving it to the desktop trash.

Use subagents only for independent bounded audits that materially reduce elapsed time. Keep release selection and edits that block the main path local.

## Select the work that applies

Use the references for the requested components; an audit does not require
building unchanged packages or activating services.

- For a full upgrade or release-freshness check, establish the current versions
  and targets with [references/release-selection.md](references/release-selection.md).
- For CLI package changes, use [references/cli-package.md](references/cli-package.md).
- For desktop packaging or compatibility work, use
  [references/desktop-package.md](references/desktop-package.md).
- Before installation or activation, use
  [references/installation.md](references/installation.md).
- For release capability changes or a requested feature review, use
  [references/feature-radar.md](references/feature-radar.md).
- After a full upgrade, or a change crossing package/runtime boundaries, use
  [references/integrated-validation.md](references/integrated-validation.md).
  Validate changed behavior; repeat checks only after further changes or to
  resolve a failure or uncertain result.

## Audit dotfiles and live runtime state

Compare configuration source, rendered state, and local overlays without exposing secrets:

- `$HOME/.dotfiles/config/codex/config.toml`;
- `${CODEX_HOME}/config.toml`;
- `${CODEX_HOME}/config.local.toml` and project-local overlays;
- the dotfiles Codex renderer and install script;
- systemd user services or sockets that run Codex binaries;
- first-party and legacy desktop installation roots, desktop entries, URL/MIME
  handlers, profiles, and package ownership;
- live and dotfiles-managed `.system` skills;
- installed plugins and their configured roots.

Use current commands where supported:

```bash
codex --version
codex features list
codex --strict-config doctor --summary --ascii --no-color
codex app-server daemon version
codex plugin list
systemctl --user status <relevant-unit>
```

Inspect service executable paths, process versions, and deleted or stale binaries after a package change. Compare release-tag system-skill samples with both the live system-skill directory and dotfiles-managed copies. Validate local skills and plugin roots when release drift could affect discovery.

Also inspect whether running Browser/JavaScript MCP workers still execute a
superseded legacy `node_repl`. Separate the persistent CLI app-server service
from the desktop app's bundled app-server and do not restart one as a substitute
for the other. Detect conflicting `codex://` handlers or desktop entries before
recommending activation of the first-party app.

Classify findings by consequence:

- **Required:** prevents startup, breaks a configured workflow, violates the new schema, or leaves an incompatible running service.
- **Recommended:** enables a useful new capability, removes meaningful drift, or improves compatibility.
- **Optional:** deliberate opt-in or cosmetic cleanup with no current breakage.
- **No change:** explicitly checked and compatible.

Prefer changing the dotfiles source of truth and rerendering over editing generated live config directly. Do not update a version review marker alone; first perform the functional audit it represents. If a service is stale after the package build or installation, report its exact restart command and current impact.

## Preserve shared app-server and remote-access ownership

Treat the systemd-managed external app-server as the authoritative machine
backend for tasks that must be available through the desktop App, LAN SSH, and
OpenAI Relay. On the packaged Linux App, require
`CODEX_APP_SERVER_USE_LOCAL_DAEMON=1` in the launcher so the App's `Local`
connection reuses that server's Unix socket. Treat a persistent App-bundled
`codex ... app-server` process as a failed handoff or compatibility fallback to
investigate before resuming the same task over SSH or Relay. Do not expose an
app-server listener directly to the LAN or internet.

For every full upgrade, and whenever the CLI, App, app-server service, remote
connections, or task ownership may change, read and follow
[references/remote-access.md](references/remote-access.md). It defines the exact
topology, read-only ownership audit, guarded service handoff, task-state
semantics, supported connection-management boundary, version map, and validation
matrix. Do not restart the shared server while a remote turn is active. Never
repair ownership or client listing by editing SQLite, LevelDB, `app.asar`, or
unverified lock files.

## Report the result

Lead with the release or audit outcome. Include the relevant versions, release
channel, artifact paths, signature/checksum provenance, changes made, validation
results, and preserved work or unresolved blockers. Distinguish a version upgrade
from a distribution migration and source-visible features from shipped behavior.

For remote-access changes, report the authoritative binary/version, service and
socket ownership, SSH/Relay state, and client/device coverage using the matrix in
[references/remote-access.md](references/remote-access.md). Do not imply that an
API check proves desktop or iOS UI behavior.

Use a feature table when material feature deltas warrant it. List remaining
privileged or disruptive actions with exact commands verified from repository
scripts or command help. Omit empty sections and unrelated feature inventories.
State any unavailable documentation, missing release assets, fallback use, and
untested requirements that limit the conclusion.
