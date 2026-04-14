---
name: github-create-pr
description: "Create GitHub pull requests from the current checkout after local commits are ready. Use when Codex needs to inspect the commit range, draft a PR title and body using the same `component: subject` and why/context rules as `draft-commit-message`, ask the user to review that text before opening the PR, then push the branch and create a draft or ready PR. Prefer this over generic publish workflows when PR wording review is required."
---

# GitHub Create PR

## Overview

Create a GitHub pull request from an existing local branch or commit range.
Draft the PR title and description first, do not add a `[codex]` prefix to
the title, and require explicit user review of the title and description
before opening the PR. Default to commit-message-style PR metadata rather
than canned GitHub template sections.

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
   - Draft the PR title using the same subject rules as
     `draft-commit-message`: prefer `<component>: <imperative summary>`,
     keep it honest, and keep it at 50 characters or fewer unless a clear
     repo-local convention requires something else.
   - If the PR is effectively one finalized commit or one squashed change,
     start from that commit subject and body verbatim. Treat the commit
     message as the default PR title/body, then make only the smallest edits
     needed for reviewer context or Markdown links.
   - Draft the PR body using the same body rules as
     `draft-commit-message`: lead with the concrete why, explain surrounding
     context that is not obvious from the diff, and do not invent missing
     rationale.
   - If the change already has a strong commit message, keep the PR title and
     body synchronized with it. Adapt only what GitHub Markdown or
     reviewer-only context requires.
   - For multi-commit PRs, synthesize from the final commit messages first.
     Prefer 1-3 short paragraphs or a short flat list over a sectioned
     template.
   - Default to plain paragraphs. Use flat bullets only when they improve
     clarity.
   - Do not default to template sections such as `Summary`, `Testing`, or
     `Checklist`. Add a labeled section only when the user explicitly asks
     for one or the material would otherwise be hard to scan.
   - If the first draft starts to look like a GitHub template, rewrite it as
     plain prose before showing it to the user.
   - For regressions, flakes, or incident fixes, put the concrete failure or
     symptom near the top so reviewers can identify the issue quickly.
   - Include exact repro or validation commands only when they materially
     support the change. Inline them naturally in the body or in a short
     supporting list. Do not force a separate `Testing` section.
   - If a short error excerpt or command is central to the why, include the
     real text rather than a placeholder.
   - Prefer short direct sentences. If a paragraph becomes a long chain of
     clauses, split it before presenting the draft.
   - Do not add `Fixes`, `Closes`, `Related`, issue numbers, commit counts, or
     stack-breakdown prose unless the user asked for them or they are already
     clearly part of the intended message.
   - When linking upstream commits or source files, keep each link aligned to
     the exact revision being discussed.
   - Prefer direct links or descriptive links over brittle intra-body anchor
     schemes. If you must use custom anchors, plan to verify the rendered body
     after PR creation.
   - Before showing the draft, compare it against the final commit message(s).
     Remove any extra framing that does not add reviewer value.
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
   - If commits were amended or squashed after the draft was first written,
     refresh the PR title/body from the final commit text before opening or
     editing the PR.
   - After creation, verify the PR head ref matches the branch that was pushed.
     If the local branch upstream points somewhere else, fix it with
     `git branch --set-upstream-to=<remote>/<branch>` so later `gh pr view`,
     `gh pr status`, and follow-up pushes resolve the same PR.
   - If the PR body uses custom anchors or other rendering-sensitive Markdown,
     verify the rendered body and fix broken links before considering the PR
     done.

5. Summarize the result.
   - Return the pushed branch, remote, base and head refs, PR URL, draft
     state, and validation that was run.

## Safety Rules

- Never open a PR before the user has reviewed and approved the PR title and
  description in the current thread.
- Never add `[codex]` or similar tool prefixes to the PR title unless the
  user explicitly asks for one.
- Never force template headings, especially `Testing`, when the same context
  reads cleanly as commit-message-style prose.
- Never decorate the first PR draft with extra issue refs, stack narration, or
  headings unless the user asked for them.
- Never stage, commit, or push unrelated user changes silently.
- If repository identity, auth, or push permissions are unclear, stop and
  explain the blocker before acting.

## PR Checklist

- title follows the same subject rules as `draft-commit-message`
- body follows the same why/context rules as `draft-commit-message`
- body avoids unnecessary template sections; `Testing` appears only when
  explicitly requested or clearly warranted
- single-commit PRs default to the finalized commit body with only minimal
  reviewer-oriented edits
- body avoids unrequested issue-closing syntax and extra framing
- debugging/incident PRs surface the failure quickly near the top
- commands, logs, and links render correctly on GitHub
- base and head branches are correct
- draft versus ready state matches the user's request

## Example Triggers

- "Create a draft PR for this branch."
- "Draft the PR title and description, let me review them, then open the PR."
- "Push these commits and create a PR after I approve the body."
