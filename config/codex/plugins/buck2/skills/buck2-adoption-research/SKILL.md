---
name: buck2-adoption-research
description: Research and implement Buck2 adoption work that bridges Bazel ecosystem expectations, including rules_go or Gazelle comparisons, BCR strategy, Starlark API compatibility, BuildBuddy Workflow bootstrap, release assets, and fixture-backed validation.
---

# Buck2 Adoption Research

Use this in `/home/nb/work/facebook/buck2` when the task is about making Buck2
easier to adopt through Bazel ecosystem compatibility or BuildBuddy-backed
workflow/release improvements. For routine fork stack refreshes, use
`$buck2-stack-maintainer` instead.

## Start

- Inspect `git status --short --branch`, current branch, remotes, and relevant
  fork refs before editing.
- Read local AGENTS.md and preserve unrelated dirty state.
- If parallel research is useful, spawn separate agents for Bazel source,
  Buck2 prelude/source, and BuildBuddy workflow evidence.

## Research Shape

- State the target user workflow first: BCR consumption, Go rules, Gazelle-style
  generated repos, Starlark compatibility, IDE/build-service integration, or
  workflow bootstrap.
- Compare Bazel behavior from source or docs against current Buck2 source.
- Separate compatibility layers:
  - public Starlark API surface
  - repo/module resolution
  - generated third-party repo metadata
  - toolchain resolution and execution platform behavior
  - BuildBuddy BES or Workflow integration

## Implementation Shape

- Prefer small, fixture-backed increments over broad compatibility rewrites.
- For Go support, validate through Buck2's representative path, not just
  `go test`. Use `bootstrap/buck2` and local platform overrides when needed.
- When scratch integration fails, verify the integration repo wiring before
  blaming the Buck2 implementation.
- Keep commit messages written with `$draft-commit-message`.

## Release And Workflow Bootstrap

- For release/bootstrap work, distinguish:
  - optimized local binary build
  - GitHub release tag and asset publication
  - Workflow update to consume the release binary
  - future bootstrap path for building Buck2 with Buck2
- BuildBuddy Workflow validation must run Buck2 itself with RBE enabled; a Cargo
  build is only a local proxy and is not representative.
- For durable `fork/main` and `fork/stack` updates, hand off to
  `$buck2-stack-maintainer` before rewriting public refs.

## Output

Return a decision matrix or implementation plan with source evidence, concrete
gaps, recommended first tickets, validation commands, and any release or workflow
risks.
