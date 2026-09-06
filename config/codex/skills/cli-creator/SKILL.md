---
name: cli-creator
description: "Create a durable, composable command-line tool from an API, SDK, web workflow, or existing script, with stable JSON and a companion skill."
---

# CLI Creator

Create a real CLI that future Codex threads can run by command name from any working directory.

This skill is for durable tools, not one-off scripts. If a short script in the current repo solves the task, write the script there instead.

## Start

Name the target tool, its source, and the first real jobs it should do:

- Source: API docs, OpenAPI JSON, SDK docs, curl examples, browser app, existing internal script, article, or working shell history.
- Jobs: literal reads/writes such as `list drafts`, `download failed job logs`, `search messages`, `upload media`, `read queue schedule`.
- Install name: a short binary name such as `ci-logs`, `slack-cli`, `sentry-cli`, or `buildkite-logs`.

Prefer a new folder under `${CLI_WORK_ROOT:-$HOME/work/cli}/<tool-name>` when the user wants a personal tool and has not named a repo.

Before scaffolding, check whether the proposed command already exists:

```bash
command -v <tool-name> || true
```

If it exists, choose a clearer install name or ask the user.

## Choose the Runtime

Before choosing, inspect the user's machine and source material:

```bash
command -v cargo rustc node pnpm npm python3 uv || true
```

Then choose the least surprising toolchain:

- Default to **Rust** for a durable CLI Codex should run from any repo: one fast binary, strong argument parsing, good JSON handling, easy copy/install into `~/.local/bin`.
- Use **TypeScript/Node** when the official SDK, auth helper, browser automation library, or existing repo tooling is the reason the CLI can be better.
- Use **Python** when the source is data science, local file transforms, notebooks, SQLite/CSV/JSON analysis, or Python-heavy admin tooling that can still be installed as a durable command.

Do not pick a language that adds setup friction unless it materially improves the CLI. If the best language is not installed, either install the missing toolchain with the user's approval or choose the next-best installed option.

State the choice in one sentence before scaffolding, including the reason and the installed toolchain you found.

## Command Contract

Sketch the command surface before coding. Include the binary name, selected
command families, applicable auth/config, and PATH/install method.

When designing the command surface, read [references/agent-cli-patterns.md](references/agent-cli-patterns.md) for the expected composable CLI shape.

Choose the parts of this surface that serve the requested jobs. An offline
transform does not need auth, discovery, writes, or a raw HTTP escape hatch:

- `tool-name --help` shows every major capability.
- `tool-name --json doctor` verifies config, auth, version, endpoint reachability, and missing setup.
- `tool-name init ...` stores local config when env-only auth is painful.
- Discovery commands find accounts, projects, workspaces, teams, queues, channels, repos, dashboards, or other top-level containers.
- Resolve commands turn names, URLs, slugs, permalinks, customer input, or build links into stable IDs so future commands do not repeat broad searches.
- Read commands fetch exact objects and list/search collections. Paginated lists support a bounded `--limit`, cursor, offset, or clearly documented default.
- Write commands do one named action each: create, update, delete, upload, schedule, retry, comment, draft. They accept the narrowest stable resource ID, support `--dry-run`, `draft`, or `preview` first when the service allows it, and do not hide writes inside broad commands such as `fix`, `debug`, or `auto`.
- `--json` returns stable machine-readable output.
- A raw escape hatch exists: `request`, `tool-call`, `api`, or the nearest honest name.

Do not expose only a generic `request` command. Give Codex high-level verbs for the repeated jobs.

Document the JSON policy in the CLI README or equivalent: API pass-through versus CLI envelope, success shape, error shape, and one example for each command family. Under `--json`, errors must be machine-readable and must not contain credentials.

## Auth and Config

For capabilities that require credentials, support the applicable paths in this
precedence order. Skip credential configuration for tools that do not need it:

1. Environment variable using the service's standard name, such as `GITHUB_TOKEN`.
2. User config under `~/.<tool-name>/config.toml` or another simple documented path.
3. `--api-key` or a tool-specific token flag only for explicit one-off tests. Prefer env/config for normal use because flags can leak into shell history or process listings.

Never print full tokens. If a diagnostic command is implemented, it should
report credential availability, the auth source category (`flag`, `env`,
`config`, provider default, or missing), and missing setup for authenticated
capabilities.

Document when the CLI or an individual mode runs without network or auth.
Existing diagnostic commands should reflect that mode and fixture availability;
do not add `doctor` solely to report that an offline tool needs no credentials.

For internal web apps sourced from DevTools curls, create sanitized endpoint notes before implementing: resource name, method/path, required headers, auth mechanism, CSRF behavior, request body, response ID fields, pagination, errors, and one redacted sample response. Never commit copied cookies, bearer tokens, customer secrets, or full production payloads.

Use screenshots to infer workflow, UI vocabulary, fields, and confirmation points. Do not treat screenshots as API evidence unless they are paired with a network request, export, docs page, or fixture.

## Build Workflow

1. Read the source just enough to inventory resources, auth, pagination, IDs, media/file flows, rate limits, and dangerous write actions. If the docs expose OpenAPI, download or inspect it before naming commands.
2. Sketch the command list in chat. Keep names short and shell-friendly.
3. Scaffold the CLI with a README or equivalent repo-facing instructions.
4. Implement the selected command families and only the requested write paths.
   Add diagnostics, discovery, ID resolution, or a raw escape hatch where they
   support those jobs.
5. Install the CLI on PATH so `tool-name ...` works outside the source folder.
6. Smoke test from another repo or `/tmp`, not only with `cargo run` or package-manager wrappers. Run `command -v <tool-name>`, `<tool-name> --help`, and a representative implemented command with a fixture or read-only input. Run `<tool-name> --json doctor` only if that diagnostic command exists.
7. Run required format and build checks, then validate meaningful behaviors such as request construction, pagination, auth failures, or fixture lookup where implemented. Avoid tests that only restate help wording or command declarations.

Use live writes for validation only when already authorized by the user's
request; otherwise prepare a fixture or preview and ask before that write.

When the source is an existing script or shell history, split the working invocation into real phases: setup, discovery, download/export, transform/index, draft, upload, poll, live write. Preserve the flags, paths, and environment variables the user already relies on, then wrap the repeatable phases with stable IDs, bounded JSON, and file outputs.

For raw escape hatches, support read-only calls first. Do not run raw non-GET/HEAD requests against a live service unless the user asked for that specific write.

For media, artifact, or presigned upload flows, test each phase separately: create upload, transfer bytes, poll/read processing status, then attach or reference the resulting ID.

For fixture-backed prototypes, keep fixtures in a predictable project path and make the CLI locate them after installation. Smoke-test from `/tmp` to catch binaries that only work inside the source folder.

For log-oriented CLIs, keep deterministic snippet extraction separate from model interpretation. Prefer a command that emits filenames, line numbers or byte ranges, matched rules, and short excerpts.

## Runtime Details

Read [references/runtime-patterns.md](references/runtime-patterns.md) for the
selected runtime's library and installation defaults.

## Companion Skill

After the CLI works, create or update a small skill for it. Use `$skill-creator` when it is available. Use `${CODEX_HOME:-$HOME/.codex}/skills/<tool-name>/SKILL.md` for a personal companion skill unless the user names a repo-local `.codex/skills/...` path or another skill repo.

Write the companion skill around the implemented jobs. Explain how to locate
the installed command and complete a common task. Include only relevant details:

- Auth/config setup when required.
- Discovery and stable ID resolution when implemented.
- The supported read or local transformation path.
- Draft/write paths and their authorization boundaries when implemented.
- A raw escape hatch when available.
- Enough concrete command examples to cover the common jobs without padding.

Keep API reference details in the CLI docs or a skill reference file. Keep the skill focused on ordering, safety, and examples future Codex threads should actually run.
