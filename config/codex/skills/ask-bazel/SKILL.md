---
name: ask-bazel
description: "Answer Bazel behavior, history, and version-specific questions from bazelbuild/bazel source, commits, and linked GitHub discussions."
---

# Ask Bazel

## Goal

Answer Bazel questions using evidence from code, history, and community context.

## Workspace Selection

Use `${BAZEL_REPO:-$HOME/work/bazelbuild/bazel}` as the primary repository.

Set `repo="${BAZEL_REPO:-$HOME/work/bazelbuild/bazel}"` before running git
commands below.

Detect whether the user gave a Bazel version/ref (tag, branch, commit SHA, release name).

When no version/ref is provided, stay on the current checkout and research directly.

When a version/ref is provided, resolve it without switching the user's
checkout:

```bash
git -C "$repo" rev-parse --verify "${ref}^{commit}"
```

If not found, fetch the needed upstream ref from GitHub and re-check. Report an
unresolved ref rather than researching a different version silently.

```bash
git -C "$repo" fetch https://github.com/bazelbuild/bazel.git "$ref"
git -C "$repo" rev-parse --verify "${ref}^{commit}"
```

For an explicitly fetched ref that has no local name, resolve `FETCH_HEAD`
immediately after the successful fetch. Use `git show <commit>:<path>`,
`git grep <pattern> <commit>`, and `git log <commit>` for read-only research.
If a checked-out tree is needed, create an isolated detached worktree or local
clone at that commit. Preserve the existing checkout and unrelated dirty work.

Always report the exact commit hash and repo path used for research.

## Research Workflow

1. Read relevant source, tests, and docs in the selected repo.
2. Use fast code search first (`rg`, `git grep`) to find symbols, flags, errors, or behavior.
   Before opening a file with `sed` or narrowing history to a path, confirm the
   path in the checked-out ref with `rg --files`, `git grep -l`, or similar when
   the exact location is not already known. Bazel moves files across packages
   often enough that guessed paths are a common source of wasted turns.
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

In Bazel-facing prose about generic remote-execution roles, use "RBE server"
and "worker". Preserve actual API, type, flag, and component names; "executor"
remains appropriate for a concrete component with that name.

Include:

1. Exact repo path and commit hash researched.
2. Key code references (file paths and symbols).
3. Relevant commits with short rationale from messages/diffs.
4. Relevant Issue/PR/Discussion links and what they add.
5. Explicit uncertainty when evidence is incomplete or conflicting.
