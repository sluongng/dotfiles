---
name: ask-buddy
description: Research and troubleshoot BuildBuddy+Bazel issues by inspecting local clones or source history for bazelbuild/bazel, buildbuddy-io/buildbuddy, buildbuddy-io/buildbuddy-toolchains, and buildbuddy-io/buildbuddy-helm. Use when Codex needs source-backed answers for BuildBuddy behavior that spans Bazel client versions, remote cache or execution, BES, executor/toolchain images, Helm chart deployment settings, Bazelisk version drift, regressions, or customer-facing Bazel+BuildBuddy failures.
---

# Ask Buddy

## Goal

Answer BuildBuddy+Bazel questions from source evidence across the repos that
can affect the behavior:

- `bazelbuild/bazel`
- `buildbuddy-io/buildbuddy`
- `buildbuddy-io/buildbuddy-toolchains`
- `buildbuddy-io/buildbuddy-helm`

Prefer local clones and exact checked-out commits. Use GitHub Issues, PRs, and
Discussions for rationale and timeline only after local source search narrows
the topic.

## Workspace Selection

First determine which repos are relevant to the symptom. Do not clone all four
repos by default.

Run the helper from this skill directory to inventory local clones and Bazel
version hints from the affected workspace:

```bash
python3 scripts/resolve_context.py --project "${PROJECT_DIR:-$PWD}"
```

Use environment variables when the user or shell already provides them:

- `BUILDBUDDY_RESEARCH_ROOT`
- `CODEX_RESEARCH_ROOT`
- `BAZEL_REPO`
- `BUILDBUDDY_REPO`
- `BUILDBUDDY_TOOLCHAINS_REPO`
- `BUILDBUDDY_HELM_REPO`

Otherwise check the generic local clone candidates reported by the helper:

- `<research-root>/bazelbuild/bazel`
- `<research-root>/buildbuddy-io/buildbuddy`
- `<research-root>/buildbuddy-io/buildbuddy-toolchains`
- `<research-root>/buildbuddy-io/buildbuddy-helm`

The helper picks `<research-root>` from `--repo-root`,
`BUILDBUDDY_RESEARCH_ROOT`, `CODEX_RESEARCH_ROOT`, then `$HOME/work`.
Runtime output may contain machine-local paths; do not copy those paths into
reusable skill instructions or examples.

These repos are large. If a needed repo is missing, ask the user to choose one
of:

1. an existing local clone path
2. a parent directory where Codex may clone the repo

Do not silently clone a missing large repo.

## Version And Ref Selection

Detect explicit repo refs in the user request first: release version, branch,
tag, commit SHA, Docker image tag, chart version, or PR number.

For Bazel, if no explicit ref is provided, use the helper's version hints:

1. `.bazelversion`
2. `.bazeliskrc` entries such as `USE_BAZEL_VERSION`
3. current `BAZEL_REPO` checkout / HEAD

If no version hint is available, default every repo to the current checkout /
HEAD. Report that this was a HEAD-based answer.

When a non-current ref is needed for a repo:

1. Check cleanliness.

```bash
git -C "$repo" status --porcelain
```

2. Prefer a detached worktree next to the clone so the user's checkout does not
   move.

```bash
worktree_parent="$(mktemp -d "$(dirname "$repo")/$(basename "$repo")-research-XXXX")"
worktree="$worktree_parent/checkout"
git -C "$repo" worktree add --detach "$worktree" "$ref"
repo="$worktree"
```

3. If worktree creation fails because the ref is unknown, fetch tags and
   branches from the canonical remote and retry:

```bash
git -C "$repo" fetch https://github.com/OWNER/REPO.git --tags --prune
git -C "$repo" rev-parse --verify "${ref}^{commit}"
git -C "$repo" worktree add --detach "$worktree" "${ref}^{commit}"
```

4. If the repo is dirty and worktrees are not suitable, clone locally with
   `--no-hardlinks` into a user-approved parent directory and research there.

Always record the exact path and commit hash used for each repo:

```bash
git -C "$repo" rev-parse HEAD
```

## Research Workflow

1. Normalize the symptom:
   - failing command, log lines, invocation URL, Helm values, platform
     properties, executor image, Bazel flags, and target labels
   - affected layer: Bazel client, BuildBuddy CLI/sidecar/server, executor,
     cache, scheduler, BES, toolchain image, or Helm deployment
   - version sources: explicit user ref, `.bazelversion`, `.bazeliskrc`, or HEAD

2. Search locally with `rg` or `git grep` before opening files. Confirm paths in
   the checked-out ref before using `sed` or narrowing history to a guessed path.

3. Trace the path by layer:
   - Bazel: flags, remote cache/execution, BES, Bazelisk, Bzlmod, repository
     rules, platform and toolchain resolution
   - BuildBuddy: frontend gates, CLI/sidecar behavior, API handlers, cache,
     scheduler, executor, bytestream, remote asset/downloader, invocation UI
   - BuildBuddy toolchains: Dockerfiles, image contents, SDK archives, platform
     properties, language/toolchain setup
   - BuildBuddy Helm: values, templates, chart defaults, config maps, secrets,
     service wiring, Redis or executor deployment settings

4. Investigate history with pickaxe or regex diffs when behavior changed:

```bash
git -C "$repo" log -p -S'needle' -- path/to/area
git -C "$repo" log -p -G'regex' -- path/to/area
```

5. Use `gh` for community and maintainer context once search terms are clear:

```bash
gh issue list --repo OWNER/REPO --search "terms" --limit 20
gh issue view NUMBER --repo OWNER/REPO --comments
gh pr list --repo OWNER/REPO --search "terms" --limit 20
gh pr view NUMBER --repo OWNER/REPO --comments
```

For GitHub Discussions, use `gh api graphql` and search titles/bodies for the
topic.

## Parallelization

Spawn subagents when independent repo slices can materially advance the work:

- one agent for Bazel source/history
- one agent for BuildBuddy source/history
- one agent for toolchains or Helm chart wiring
- one agent for GitHub Issues/PRs/Discussions

Pass each subagent the repo path, checked-out commit, and narrow symptom. Merge
findings only after verifying that versions, commits, and layer boundaries agree.

## Output

Return concise, evidence-backed answers. Include:

1. repo paths and exact commit hashes researched
2. Bazel version source: explicit ref, `.bazelversion`, `.bazeliskrc`, or HEAD
3. key source references and symbols
4. relevant commits and the rationale visible in messages or diffs
5. relevant Issue/PR/Discussion links and what they add
6. clear layer attribution for the root cause or uncertainty
7. next checks or validation commands when source evidence is not enough

Redact API keys, invocation tokens, private URLs, and customer identifiers before
sharing output.
