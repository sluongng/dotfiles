---
name: upgrade-codex-stack
description: On the Arch Linux workstation, upgrade and audit the local Codex CLI package, first-party Linux ChatGPT/Codex App distribution, Arch desktop packaging, shared app-server and SSH/OpenAI Relay topology, legacy repackager fallback, configuration, skills, plugins, services, and feature maturity. Do not use this Linux packaging workflow for macOS Codex upgrades.
---

# Upgrade Codex Stack

This is the Arch Linux workstation upgrade workflow. If `uname -s` is not
`Linux`, stop before using any `/home/nb`, pacman, systemd, or Linux desktop app
steps and use the platform's normal Codex distribution/update path instead.

Upgrade the complete local Codex stack and finish with a current-state report. Treat the CLI package, desktop app, desktop runtime, rendered configuration, plugins, system skills, and services as one system while preserving the boundary between their responsibilities.

## Scope and Safety

Use these default paths unless the user supplies different ones:

- Codex source and workspace: `/home/nb/work/misc/codex`
- Arch package: `/home/nb/work/misc/codex/openai-codex-pkg`
- Linux desktop packaging and legacy repackager: `/home/nb/work/misc/codex-app`
- Dotfiles source of truth: `/home/nb/.dotfiles`
- Live Codex home: `${CODEX_HOME:-$HOME/.codex}`

Before editing:

1. Read every applicable `AGENTS.md` for each repository in scope.
2. Run `git status --short` and inspect relevant existing diffs in every repository.
3. Preserve all pre-existing work and distinguish it from changes made during this run.
4. Use official upstream release metadata, source, documentation, and artifacts as primary evidence.
5. Never print credentials, cookies, tokens, or unredacted authentication payloads.

Build and update the scoped repositories when the user requests an upgrade. Do not use `sudo`, install a built package, replace the installed desktop app, register package repositories, run foreign-package maintainer scripts, restart services, or overwrite live config unless the user explicitly requests that disruptive action. Return exact deferred commands in the final report.

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

## 1. Establish the Baseline and Target Releases

Record the current state before changing anything:

- installed and packaged Codex CLI versions;
- running CLI, app-server daemon, and service versions;
- current package source URLs and checksums;
- current desktop app version, installation path, distribution channel
  (first-party Linux or legacy macOS-derived), and packaged output;
- the binary and version serving each path: the interactive system CLI, shared
  app-server, desktop App Local host, SSH proxy backend, code-mode host, and
  Browser/JavaScript MCP runtime;
- shared app-server socket ownership, systemd service state, OpenAI Relay state,
  saved App SSH connections, and any active or idle loaded remote tasks;
- relevant repository commits, branches, dirty files, and upstream remotes;
- enabled/default feature flags and plugin state.

Select the latest packageable CLI alpha by checking both the npm registry metadata for `@openai/codex` and the matching official GitHub release. Do not select a tag merely because it sorts newest. Require the release assets consumed by the package, including the Linux musl CLI package and responses API proxy. If the newest alpha lacks required assets, choose the newest complete alpha and explain the gap.

Determine the desktop app target from current official Linux release metadata and
artifacts. Use the official product/download page and signed APT or RPM repository
metadata as primary evidence. Record the release date, package version,
architecture, artifact URL, size, checksum, signing identity, supported distro
matrix, and the version of the embedded Codex CLI. Do not infer freshness from a
redirect filename or compare desktop and CLI versions as if they shared a release
line.

Prefer the newest verifiable first-party Linux package. Use the macOS appcast via
the repository's `release-info` command only when auditing the legacy fallback or
when the first-party package is missing, unverifiable, or unusable. If falling
back, state the exact reason and compare both channels' versions and release
dates.

## 2. Upgrade the Arch CLI Package

Work with the existing `PKGBUILD`; do not replace its packaging design. Preserve user modifications and the `/usr/lib/openai-codex` layout unless upstream now requires a justified migration.

1. Update `pkgver`, sources, asset names, and checksums for the selected alpha.
2. Preserve Arch alpha version ordering, converting upstream separators only as required by pacman version syntax.
3. Refresh `.SRCINFO` from `makepkg --printsrcinfo`.
4. Verify that the package still installs the primary binary and expected helpers, including `codex-code-mode-host`, sandbox support, `rg`, `zsh`, and the responses API proxy when present in the established package.
5. Do not add the desktop `node_repl` runtime to this package solely because CLI code mode exists. CLI code mode uses `codex-code-mode-host`; add another runtime only after finding a real CLI consumer and an upstream path contract.

Run proportionate packaging validation:

```bash
makepkg --verifysource
makepkg -Ccf
diff -u .SRCINFO <(makepkg --printsrcinfo)
pacman -Qip ./<package-file>
pacman -Qlp ./<package-file>
```

Extract the built package into a temporary directory, run its embedded `codex --version`, and inspect helper binary types. Report the exact artifact path, version, package layout result, and deferred `sudo pacman -U ...` command.

## 3. Upgrade and Validate the Linux Desktop App

Always include `/home/nb/work/misc/codex-app` in a full run. Follow its repository
instructions and existing scripts. Evolve that repository's packaging path when
the user requests an upgrade; do not build a one-off package outside it.

### Prefer the first-party Linux package

1. Discover the current `.deb` or `.rpm` from an official OpenAI page or signed
   package repository. Select the host architecture explicitly.
2. Verify signed repository metadata and then verify the downloaded artifact
   against its exact size and SHA-256. Record the signing-key fingerprint from
   the verified metadata; allow legitimate key rotation instead of hardcoding a
   historical fingerprint as permanent truth. State precisely whether trust
   comes from signed repository metadata authenticating the package hash, a
   per-package signature, or both; do not describe an unsigned `.deb` as
   directly signed.
3. Inspect package metadata, file layout, dependencies, desktop/MIME handlers,
   AppArmor policy, and maintainer scripts before building or installing
   anything. Treat maintainer scripts as untrusted-to-run during inspection.
4. On Arch/CachyOS, never install the `.deb` with `dpkg`, add its APT repository,
   or execute its maintainer scripts. Use the repository's Arch-native wrapper
   for the official payload. If none exists and the user requested an upgrade,
   add the smallest maintainable wrapper to that repository rather than
   extending the legacy macOS conversion path.
5. Preserve the vendor application payload and native runtimes byte-for-byte
   unless a concrete host incompatibility proves a patch is necessary. Keep the
   first-party layout and names, including the unified ChatGPT branding, rather
   than rewriting them to resemble the legacy package. Treat vendor binaries and
   resources as the immutable payload boundary; Arch package metadata, launchers,
   and host-integration files may differ when necessary and must be reviewed
   explicitly.
6. Build a pacman-inspectable artifact and check package ownership, conflicts,
   upgrade behavior, desktop entry, URL scheme, MIME registration, and any
   coexistence rules with the legacy installation.

Validate the first-party payload before activation using isolated `HOME`,
`CODEX_HOME`, and XDG directories. At minimum check:

- package signature provenance, checksum, architecture, ELF types, and unresolved
  shared libraries;
- renderer startup and the bundled app-server initialization handshake;
- bundled `codex --version`, `codex-code-mode-host`, and `rg`;
- `node_repl` MCP initialization, tool listing, JavaScript evaluation, and the
  Browser bridge;
- clean process shutdown and absence of probe processes afterward.

Do not interpret an isolated probe's missing login or failed `codex://`
registration as a product failure. Those require an installed desktop session.
Do not copy browser cookies, app credentials, or authentication state between
profiles; use the application's supported sign-in flow when installation is
authorized.

### Use the legacy repackager only as fallback

If the first-party Linux release cannot be used, resolve the macOS target with
`npm run release-info -- --json` or the current equivalent and use the existing
forced repackage, install, and smoke-test commands. Patch only concrete bundle
drift or Linux compatibility failures. For this path, continue verifying the
pinned Linux `node_repl`, manifest/checksum, GLIBC compatibility, Browser
native-pipe behavior, and required compatibility patches. Refresh checked-in
fixtures only when their source bundle changed.

Keep the runtime boundary explicit in the report: the desktop app's `node_repl`
serves Browser/JavaScript MCP, while CLI code mode uses
`codex-code-mode-host`. The first-party package should supply native Linux builds
of both; the legacy path may source them separately.

Do not install, switch the active desktop entry, migrate a profile, or restart
the app by default. Prefer a side-by-side first-party installation and distinct
profile for initial parity testing only after checking app IDs, single-instance
locks, DBus names, URL/MIME handlers, and profile paths for collisions. If those
cannot be isolated, use an extracted-package probe instead of simultaneous
activation. Report the generated Arch artifact, the channel used, and only
installation/switch commands verified from the repository or package metadata.

## 4. Audit Dotfiles and Live Runtime State

Compare configuration source, rendered state, and local overlays without exposing secrets:

- `/home/nb/.dotfiles/config/codex/config.toml`;
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

## 5. Preserve Shared App-Server and Remote-Access Ownership

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

## 6. Produce a Current Feature Radar

Use the `$openai-docs` skill to consult the current official Codex and desktop-app
documentation. Documentation lookup is read-only and remains required during an
audit-only run; skip it only when the helper or upstream source is unavailable,
and report the exact freshness limitation. For a new Linux preview, cross-check
the official announcement, support matrix, product/download page, and signed
package repository because general desktop documentation may lag the release.
Also inspect the target release notes, source at the target tag, changes since the
previously installed or packaged version, and `codex features list`.

Cover practical user-facing changes in all relevant maturity classes:

- stable or newly default-enabled;
- experimental or opt-in;
- under development or source-visible but not yet supported;
- newly deprecated, renamed, or removed.

For each material feature, report:

1. maturity and availability in the target release;
2. upstream default state;
3. whether it is enabled or configured on this machine;
4. what changed since the prior version;
5. practical impact for this user's workflows;
6. a concrete way to test it;
7. whether a dotfiles change is required, recommended, optional, or unnecessary.

Distinguish shipped behavior from source-only work and supported features from experiments. Focus on material deltas rather than listing every unchanged flag. Explicitly check code mode and its host, multi-agent behavior, tool permissions, plugins and MCP, Browser/computer-use paths, memory/context behavior, TUI/app-server/remote-control behavior, and any feature family changed by the target release.

If current documentation, release metadata, or an upstream service is unavailable, continue with verified local artifacts where possible and label the freshness limitation. Never present an inference as a confirmed release fact.

## 7. Validate the Integrated Result

Repeat version and configuration checks against the newly built artifacts. Confirm that:

- package metadata, contents, and embedded versions agree;
- the desktop artifact came from the selected first-party or fallback channel,
  and its signature/checksum evidence is recorded;
- the desktop package passes its smoke and relevant runtime tests;
- a first-party payload remains unmodified unless a documented compatibility
  failure required a narrowly scoped patch;
- the Arch package does not depend on executing Debian or RPM maintainer scripts;
- first-party and legacy desktop entries, profiles, and URL handlers have an
  explicit coexistence or migration plan;
- source config renders consistently or documented local overlays explain the difference;
- feature recommendations match the target binary rather than only upstream main;
- the systemd-managed `MainPID` owns the shared app-server socket, or any
  intentional deviation is explained;
- the desktop App's `Local` connection reuses the shared daemon and does not
  leave a persistent App-bundled app-server process;
- LAN SSH and the App's SSH connection attach through `codex app-server proxy`
  without starting a competing authoritative server;
- OpenAI Relay reaches a connected state after any transient takeover period;
- a dormant shared task can be listed, read, and opened through the intended
  host without concurrent Local/remote writer ownership;
- desktop and iOS UI visibility are reported separately from API visibility,
  with unperformed actual-device checks labeled as such;
- an authorized App restart preserves or reconnects the saved SSH connection;
- no unrelated dirty files were overwritten;
- no required install or restart was silently performed.

For an upgrade that changes the CLI, desktop App, app-server service, or
connection state, include the matrix from
[references/remote-access.md](references/remote-access.md) and mark each row
pass, fail, not tested, or not applicable.

On Hyprland, add a lightweight post-upgrade smoke check for the main window,
right-click menus and popovers, pet placement/workspace following, unexpected
focus activation, and compositor configuration errors. Route failures to the
`desktop-incident-triage` skill; do not turn this package-upgrade workflow into a
compositor repair or patch the vendor payload for a window-management symptom.

Do not call the run complete when a required build, smoke test, or configuration check failed. State the blocker, preserve useful artifacts, and give the smallest recovery step.

## Final Report

Always end with these headings, even when a section has no changes:

```markdown
## Release outcome
## CLI package
## Desktop app
## Runtime and code mode
## Remote access and writer ownership
## Dotfiles and live-state audit
## Feature radar
## Validation
## Actions for the user
## Preserved work and blockers
```

Include actual versions, dates, artifact paths, release channel, signing/checksum
evidence, and test results. State whether a desktop version change occurred or
whether the result is only a distribution/support-path migration. Use a compact
feature table with columns for feature, maturity, default/enabled state,
practical impact, and recommendation. Separate changes made from findings
reported only. Under **Remote access and writer ownership**, include the
authoritative server binary/version, service state and `MainPID`, socket owner,
SSH proxy and Relay state, saved App connection state, Local/remote task
ownership, actual-device coverage, and any UI-listing or deep-link limitation.
Under **Actions for the user**, include only remaining privileged
or disruptive steps with exact commands whose availability was verified from
repository scripts or command help; write `None` if there are none. Explicitly
state unsupported-host risk, degraded documentation freshness, missing release
assets, preserved pre-existing changes, fallback status, and unresolved
blockers.
