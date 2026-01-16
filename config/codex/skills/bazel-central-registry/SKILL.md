---
name: bazel-central-registry
description: Work with Bazel Central Registry (BCR) modules and bzlmod dependencies. Use for finding modules/versions in a BCR checkout, checking latest BCR versions, upgrading `bazel_dep` entries in `MODULE.bazel` (including includes), and analyzing dependency trees via the bundled `scripts/bcr_tool.py` and upstream `scripts/registry.py`.
---

# Bazel Central Registry

## Overview
Use this skill to query BCR module metadata, update bzlmod dependencies, and inspect dependency trees. The skill bundles the upstream `registry.py` helper and a thin CLI (`bcr_tool.py`) that wraps common workflows.

## Quick start

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

### Find modules / versions (local registry clone)
1. Clone or point at a local bazel-central-registry checkout.
2. Search by substring:
   - `python3 scripts/bcr_tool.py find --registry-path /path/to/bazel-central-registry --query rules_`
3. List versions for a module:
   - `python3 scripts/bcr_tool.py list-versions --registry-path /path/to/bazel-central-registry --module rules_go`

### Upgrade modules in MODULE.bazel
- `upgrade` reads the root `MODULE.bazel`, follows `include()` files, and updates `bazel_dep(..., version = "...")` entries to the latest BCR version.
- Use `--module` to target a subset and `--include-overrides` to update `single_version_override` entries.
- Always start with a dry-run, then re-run with `--write` when the diff looks correct.

### Analyze dependency tree
- `list-deps` shows direct deps (names + versions) from all included module files.
- `deps-tree` fetches MODULE.bazel files from BCR for a best-effort transitive tree (bounded by `--max-depth`).
- For a fully resolved graph (including overrides/extensions), run Bazel directly:
  - `bazel mod graph`

## Resources

### scripts/
- `registry.py`: upstream BCR registry helper (used for metadata and downloads).
- `bcr_tool.py`: CLI wrapper for module search, latest version lookup, upgrades, and dependency inspection.
