---
name: upgrade-codex-stack
description: On the Arch Linux workstation, upgrade and audit the local Codex CLI package, Linux Codex App repackager, configuration, skills, plugins, services, and feature maturity. Do not use this Linux packaging workflow for macOS Codex upgrades.
---

# Upgrade Codex Stack

This is the Arch Linux workstation upgrade workflow. If `uname -s` is not
`Linux`, stop before using any `/home/nb`, pacman, systemd, or Linux Codex App
steps and use the platform's normal Codex distribution/update path instead.

Upgrade the complete local Codex stack and finish with a current-state report. Treat the CLI package, Codex App, desktop runtime, rendered configuration, plugins, system skills, and services as one system while preserving the boundary between their responsibilities.

## Scope and Safety

Use these default paths unless the user supplies different ones:

- Codex source and workspace: `/home/nb/work/misc/codex`
- Arch package: `/home/nb/work/misc/codex/openai-codex-pkg`
- Linux Codex App: `/home/nb/work/misc/codex-app`
- Dotfiles source of truth: `/home/nb/.dotfiles`
- Live Codex home: `${CODEX_HOME:-$HOME/.codex}`

Before editing:

1. Read every applicable `AGENTS.md` for each repository in scope.
2. Run `git status --short` and inspect relevant existing diffs in every repository.
3. Preserve all pre-existing work and distinguish it from changes made during this run.
4. Use official upstream release metadata, source, documentation, and artifacts as primary evidence.
5. Never print credentials, cookies, tokens, or unredacted authentication payloads.

Build and update the scoped repositories when the user requests an upgrade. Do not use `sudo`, install a built package, replace the installed desktop app, restart services, or overwrite live config unless the user explicitly requests that disruptive action. Return exact deferred commands in the final report.

Use subagents only for independent bounded audits that materially reduce elapsed time. Keep release selection and edits that block the main path local.

## 1. Establish the Baseline and Target Releases

Record the current state before changing anything:

- installed and packaged Codex CLI versions;
- running CLI, app-server daemon, and service versions;
- current package source URLs and checksums;
- current Codex App version and packaged output;
- relevant repository commits, branches, dirty files, and upstream remotes;
- enabled/default feature flags and plugin state.

Select the latest packageable CLI alpha by checking both the npm registry metadata for `@openai/codex` and the matching official GitHub release. Do not select a tag merely because it sorts newest. Require the release assets consumed by the package, including the Linux musl CLI package and responses API proxy. If the newest alpha lacks required assets, choose the newest complete alpha and explain the gap.

Determine the Codex App target from the appcast through the repository's release-info command. Prefer the latest upstream app release that the repackager supports, and record its release date and source identifier.

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

## 3. Upgrade and Validate Codex App

Always include `/home/nb/work/misc/codex-app` in a full run. Follow its repository instructions and existing scripts instead of duplicating repackaging logic.

1. Resolve the target with `npm run release-info -- --json` or the current equivalent.
2. Install JavaScript dependencies only when the lockfile or repository state requires it.
3. Run the repository's forced repackage command for the target version.
4. Patch only concrete upstream bundle drift or Linux compatibility failures exposed by the build.
5. Refresh checked-in automation examples or fixtures when their source bundle changed.
6. Run the repository smoke test and relevant extension-host or MCP tests.

Ensure the Linux primary runtime bundled for Browser/JavaScript MCP is valid:

- `node_repl` must be the pinned Linux executable, not a copied Mach-O binary;
- pin and verify its checksum and manifest metadata;
- verify ELF architecture and required shared-library compatibility;
- retain or refresh the weak `pidfd_*` compatibility patch where the target glibc needs it;
- retain or refresh Browser native-pipe and trust patches when upstream code paths changed;
- test MCP initialization, tool listing, JavaScript evaluation, and the Browser bridge when those paths are packaged.

Keep the runtime boundary explicit in the report: the desktop app's `node_repl` serves Browser/JavaScript MCP, while CLI code mode uses `codex-code-mode-host`.

Do not install or restart Codex App by default. Report the generated package or install path and the exact deferred installation command.

## 4. Audit Dotfiles and Live Runtime State

Compare configuration source, rendered state, and local overlays without exposing secrets:

- `/home/nb/.dotfiles/config/codex/config.toml`;
- `${CODEX_HOME}/config.toml`;
- `${CODEX_HOME}/config.local.toml` and project-local overlays;
- the dotfiles Codex renderer and install script;
- systemd user services or sockets that run Codex binaries;
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

Classify findings by consequence:

- **Required:** prevents startup, breaks a configured workflow, violates the new schema, or leaves an incompatible running service.
- **Recommended:** enables a useful new capability, removes meaningful drift, or improves compatibility.
- **Optional:** deliberate opt-in or cosmetic cleanup with no current breakage.
- **No change:** explicitly checked and compatible.

Prefer changing the dotfiles source of truth and rerendering over editing generated live config directly. Do not update a version review marker alone; first perform the functional audit it represents. If a service is stale after the package build or installation, report its exact restart command and current impact.

## 5. Produce a Current Feature Radar

Use the `$openai-docs` skill to consult the current official Codex documentation. Documentation lookup is read-only and remains required during an audit-only run; skip it only when the helper or upstream source is unavailable, and report the exact freshness limitation. Also inspect the target release notes, source at the target tag, changes since the previously installed or packaged version, and `codex features list`.

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

## 6. Validate the Integrated Result

Repeat version and configuration checks against the newly built artifacts. Confirm that:

- package metadata, contents, and embedded versions agree;
- the Codex App package passes its smoke and relevant runtime tests;
- source config renders consistently or documented local overlays explain the difference;
- feature recommendations match the target binary rather than only upstream main;
- no unrelated dirty files were overwritten;
- no required install or restart was silently performed.

Do not call the run complete when a required build, smoke test, or configuration check failed. State the blocker, preserve useful artifacts, and give the smallest recovery step.

## Final Report

Always end with these headings, even when a section has no changes:

```markdown
## Release outcome
## CLI package
## Codex App
## Runtime and code mode
## Dotfiles and live-state audit
## Feature radar
## Validation
## Actions for the user
## Preserved work and blockers
```

Include actual versions, dates, artifact paths, and test results. Use a compact feature table with columns for feature, maturity, default/enabled state, practical impact, and recommendation. Separate changes made from findings reported only. Under **Actions for the user**, include only remaining privileged or disruptive steps with exact commands whose availability was verified from repository scripts or command help; write `None` if there are none. Explicitly state any degraded freshness, missing release assets, preserved pre-existing changes, and unresolved blockers.
