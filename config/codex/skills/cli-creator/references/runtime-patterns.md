# Runtime and Installation Patterns

Read only the section for the selected runtime. These are defaults; match the
existing project and the user's choices when they differ.

## Rust Defaults

When building in Rust, use established crates instead of custom parsers:

- `clap` for commands and help
- `reqwest` for HTTP
- `serde` / `serde_json` for payloads
- `toml` for small config files
- `anyhow` for CLI-shaped error context

Add a `Makefile` target such as `make install-local` that builds release and installs the binary into `~/.local/bin`.

## TypeScript/Node Defaults

When building in TypeScript/Node, keep the CLI installable as a normal command:

- `commander` or `cac` for commands and help
- native `fetch`, the official SDK, or the user's existing HTTP helper for API calls
- `zod` only where external payload validation prevents real breakage
- `package.json` `bin` entry for the installed command
- `tsup`, `tsx`, or `tsc` using the repo's existing convention

Add an install path such as `pnpm install`, `pnpm build`, and `pnpm link --global`, or a `Makefile` target that installs a small wrapper into `~/.local/bin`.

## Python Defaults

When building in Python, prefer boring standard-library pieces unless the workflow needs more:

- `argparse` for commands and help, or `typer` when subcommands would otherwise get messy
- `urllib.request` / `urllib.parse`, `requests`, or `httpx` for HTTP, matching what is already installed or already used nearby
- `json`, `csv`, `sqlite3`, `pathlib`, and `subprocess` for local files, exports, databases, and existing scripts
- `pyproject.toml` console script or a small executable wrapper for the installed command
- `uv` or a virtualenv only when dependencies are actually needed

Add a `Makefile` target such as `make install-local` that installs the command on PATH and document whether it depends on `uv`, a virtualenv, or only system Python.
