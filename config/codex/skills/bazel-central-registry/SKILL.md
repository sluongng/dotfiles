---
name: bazel-central-registry
description: Inspect Bazel Central Registry (BCR) modules and bzlmod dependencies. Use when Codex needs to find BCR modules or versions, audit which direct deps in a repo are upgradeable, compare current pins to live BCR releases, update `bazel_dep` or `single_version_override` entries in `MODULE.bazel` (including `include()` files), or inspect module dependency trees.
---

# Bazel Central Registry

Use this skill to inspect live BCR metadata, answer repo-local Bzlmod version questions, and update module pins.

## Quick start

- Check which direct deps in a repo can be upgraded:
  - `python3 scripts/bcr_tool.py check-upgrades --module-file /path/to/MODULE.bazel`
- Check one included file only:
  - `python3 scripts/bcr_tool.py check-upgrades --module-file /path/to/deps/bazel_dep.MODULE.bazel --workspace-root /path/to/workspace`
- List direct deps from a workspace (follows `include()` chains):
  - `python3 scripts/bcr_tool.py list-deps --module-file /path/to/MODULE.bazel`
- Check latest versions from BCR:
  - `python3 scripts/bcr_tool.py latest --module rules_go --module rules_python`
- Dry-run upgrade (print diffs only):
  - `python3 scripts/bcr_tool.py upgrade --module-file /path/to/MODULE.bazel`
- Apply upgrade edits:
  - `python3 scripts/bcr_tool.py upgrade --module-file /path/to/MODULE.bazel --write`
- Best-effort dependency tree (bounded depth):
  - `python3 scripts/bcr_tool.py deps-tree --module-file /path/to/MODULE.bazel --max-depth 2`

## Tasks

### Check which modules can be upgraded
1. Use `check-upgrades` first for questions like "which modules in the current repo can be upgraded?"
2. Point `--module-file` at the root `MODULE.bazel` when the repo uses `include()`.
3. Point `--module-file` at an included file when the user wants a scoped answer for one file such as `deps/bazel_dep.MODULE.bazel`; pass `--workspace-root` if that file contains labels that should resolve from the repo root.
4. Treat `single_version_override(..., version = "...")` as the effective version when comparing to BCR.
5. Treat `archive_override` and versionless deps as custom pins. Report them separately instead of claiming they can be upgraded by a simple BCR version bump.
6. Cite exact file and line numbers from the tool output in the answer.

### Find modules / versions (local registry clone)
1. Clone or point at a local bazel-central-registry checkout.
2. Search by substring:
   - `python3 scripts/bcr_tool.py find --registry-path /path/to/bazel-central-registry --query rules_`
3. List versions for a module:
   - `python3 scripts/bcr_tool.py list-versions --registry-path /path/to/bazel-central-registry --module rules_go`

### Upgrade modules in MODULE.bazel
- Start with `check-upgrades` or a dry-run `upgrade` before editing files.
- `upgrade` reads the root `MODULE.bazel`, follows `include()` files, and updates `bazel_dep(..., version = "...")` entries to the latest BCR version.
- Use `--module` to target a subset and `--include-overrides` to update `single_version_override` entries.
- By default, live lookups choose the latest non-yanked stable release. Add `--include-prerelease` only when the user explicitly wants release candidates or betas.
- Always start with a dry-run, then re-run with `--write` when the diff looks correct.
- After bumps, check whether the repo also pins the same dependency on another surface such as `go.mod`, lockfiles, or generated manifests.

### Analyze dependency tree
- `list-deps` shows direct deps (names + versions) from all included module files.
- `deps-tree` fetches MODULE.bazel files from BCR for a best-effort transitive tree (bounded by `--max-depth`).
- For a fully resolved graph (including overrides/extensions), run Bazel directly:
  - `bazel mod graph`

## Resources

### scripts/
- `bcr_tool.py`: primary CLI for module search, live metadata lookup, upgrade checks, upgrades, and dependency inspection.
- `registry.py`: upstream BCR reference helper kept for comparison and reuse when needed.
