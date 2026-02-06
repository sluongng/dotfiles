---
name: ask-bazel
description: Research and answer Bazel questions by reading the Bazel source tree, commit history, and GitHub context (Issues, PRs, Discussions). Use when the user asks how Bazel works, why behavior changed, when a feature/regression appeared, or asks version-specific Bazel questions tied to bazelbuild/bazel.
---

# Ask Bazel

## Goal

Answer Bazel questions using evidence from code, history, and community context.

## Workspace Selection

Use `~/work/bazelbuild/bazel` as the primary repository.

Set `repo=~/work/bazelbuild/bazel` before running git commands below.

Detect whether the user gave a Bazel version/ref (tag, branch, commit SHA, release name).

When no version/ref is provided, stay on the current checkout and research directly.

When a version/ref is provided, follow this exact flow:

1. Check repository cleanliness.

```bash
git -C ~/work/bazelbuild/bazel status --porcelain
```

2. If clean, resolve and checkout that version/ref in place.
3. If dirty, create a local clone first and use the clone for all versioned research.

```bash
tmp_repo="$(mktemp -d ~/work/bazelbuild/bazel-codex-XXXX)"
git clone --no-hardlinks ~/work/bazelbuild/bazel "$tmp_repo"
repo="$tmp_repo"
```

4. Verify the ref exists locally.

```bash
git -C "$repo" rev-parse --verify "${ref}^{commit}"
```

5. If not found, fetch from GitHub and re-check.

```bash
git -C "$repo" fetch https://github.com/bazelbuild/bazel.git --tags --prune
git -C "$repo" rev-parse --verify "${ref}^{commit}"
```

6. If still not found, report that the version/ref could not be resolved.
7. If found, checkout detached at the exact commit.

```bash
git -C "$repo" checkout --detach "${ref}^{commit}"
```

Always report the exact commit hash and repo path used for research.

## Research Workflow

1. Read relevant source, tests, and docs in the selected repo.
2. Use fast code search first (`rg`, `git grep`) to find symbols, flags, errors, or behavior.
3. Investigate history with pickaxe and regex diffs:

```bash
git -C "$repo" log -p -S'needle' -- path/to/area
git -C "$repo" log -p -G'regex' -- path/to/area
```

4. Review commit messages for rationale and links to issues/PRs.
5. Use `gh` to gather community and maintainer context:

```bash
gh issue list --repo bazelbuild/bazel --search "terms" --limit 20
gh issue view <number> --repo bazelbuild/bazel --comments
gh pr list --repo bazelbuild/bazel --search "terms" --limit 20
gh pr view <number> --repo bazelbuild/bazel --comments
```

For Discussions, query GraphQL via `gh api graphql` against `bazelbuild/bazel` and search titles/bodies for the topic.

## Parallelization

Spawn subagents when useful:

1. One agent for local code understanding.
2. One agent for commit-history and pickaxe analysis.
3. One agent for GitHub Issues/PRs/Discussions.

Merge findings only after verifying they agree on key facts (version, behavior, timeline).

## Response Requirements

Return concise, evidence-backed answers.

Include:

1. Exact repo path and commit hash researched.
2. Key code references (file paths and symbols).
3. Relevant commits with short rationale from messages/diffs.
4. Relevant Issue/PR/Discussion links and what they add.
5. Explicit uncertainty when evidence is incomplete or conflicting.
