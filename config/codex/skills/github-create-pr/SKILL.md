---
name: github-create-pr
description: "Create GitHub pull requests from the current checkout after local commits are ready. Use when the user wants Codex to inspect the commit range, draft the PR title and description, ask the user to review that title and description before opening the PR, then push the branch and create a draft or ready PR. Prefer this over generic publish workflows when PR wording review is required."
---

# GitHub Create PR

## Overview

Create a GitHub pull request from an existing local branch or commit range.
Draft the PR title and description first, do not add a `[codex]` prefix to
the title, and require explicit user review of the title and description
before opening the PR.

## Workflow

1. Confirm the PR scope.
   - Run `git status -sb` and inspect the commit range that will be sent.
   - If there are uncommitted or unrelated changes, stop and clarify scope.
   - If there is no coherent commit range yet, stop and ask the user to
     finish the commit workflow first.
   - Check repo-local guidance such as `AGENTS.md` before choosing branch,
     remote, or base branch behavior.

2. Draft the PR title and description before any PR creation action.
   - Inspect the commits and diff that will be included.
   - Draft a plain PR title with no `[codex]` prefix.
   - Draft a Markdown PR description that explains what changed, why, and
     how it was tested.
   - Show the proposed title and description to the user for review.
   - Treat explicit approval in the current thread as required before
     continuing. If approval is missing, stop here.

3. Prepare the branch for review.
   - If the current branch does not match repo-local PR branch conventions,
     create or rename it only when needed and only after understanding the
     repository's expectations.
   - Push the branch to the appropriate remote after the user has approved
     the PR title and description.
   - Prefer repo-local remote conventions over generic defaults.
   - Record the exact remote head ref used for the PR, especially for fork
     workflows where the pushed branch name may differ from the local upstream.

4. Open the PR.
   - Default to a draft PR unless the user explicitly asks for a ready PR.
   - Prefer the GitHub connector or app for PR creation after the branch is
     pushed.
   - Use `gh` for auth checks, repo metadata, or cross-repo `head` cases
     where the connector path is awkward.
   - Use the user-approved title and description verbatim aside from trivial
     formatting cleanup.
   - Derive the base branch from the user request or the remote default
     branch when unspecified.
   - After creation, verify the PR head ref matches the branch that was pushed.
     If the local branch upstream points somewhere else, fix it with
     `git branch --set-upstream-to=<remote>/<branch>` so later `gh pr view`,
     `gh pr status`, and follow-up pushes resolve the same PR.

5. Summarize the result.
   - Return the pushed branch, remote, base and head refs, PR URL, draft
     state, and validation that was run.

## Safety Rules

- Never open a PR before the user has reviewed and approved the PR title and
  description in the current thread.
- Never add `[codex]` or similar tool prefixes to the PR title unless the
  user explicitly asks for one.
- Never stage, commit, or push unrelated user changes silently.
- If repository identity, auth, or push permissions are unclear, stop and
  explain the blocker before acting.

## PR Checklist

- title matches repo conventions and user intent
- description explains what changed, why, and testing
- base and head branches are correct
- draft versus ready state matches the user's request

## Example Triggers

- "Create a draft PR for this branch."
- "Draft the PR title and description, let me review them, then open the PR."
- "Push these commits and create a PR after I approve the body."
