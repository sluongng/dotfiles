---
name: draft-commit-message
description: "Draft or review reader-friendly Git commit messages and PR titles and bodies from diffs or task context, following Git contribution guidance and repository conventions."
---

# Draft Commit Message

## Goal

Turn staged changes, diffs, commit ranges, or plain-English summaries into
commit messages and PR title/body source text that help readers understand what
changes and why it matters, following the Git project's `MyFirstContribution`
guidance without inventing missing rationale. Explain the change, not the
investigation that led to it.

## Workflow

1. Gather context from the repository before drafting.

Prefer staged changes first:

```bash
git status --short
git diff --cached --stat
git diff --cached
```

If nothing is staged, inspect the worktree diff instead:

```bash
git diff --stat
git diff
```

When drafting PR title/body text, inspect the final commit range as well:

```bash
git log --reverse --format=fuller --stat <base>..HEAD
git log --reverse -p <base>..HEAD
```

Also read the concrete prompt, issue, review thread, CI failure, reproducer, or
user report when it explains why the change matters. Do not stop at the diff
when reviewer context is available nearby.

2. Infer the component prefix from the narrowest dominant area of change.

- Prefer repository-local terminology from paths, packages, commands, or
  existing commit subjects.
- When the prefix is unclear, inspect recent history for the touched path:

```bash
git log --format=%s -- path/to/area | head -n 20
```

- If one commit spans unrelated areas and no honest single prefix works,
  recommend splitting the change into multiple commits.

3. Draft the subject as `<component>: <imperative summary>`.

- Keep the subject at 50 characters or fewer.
- Write in imperative mood, as if instructing the codebase: `add`, `teach`,
  `fix`, `remove`, `refactor`.
- Describe the behavior or purpose rather than listing low-level code changes.
- When used as a PR title, use this subject as the title unless repo-local PR
  conventions clearly require a different shape.

4. Bring the reader onboard with the change.

- Do not assume readers are technical users or know the code, prior discussion,
  or project vocabulary. Follow a stated audience; otherwise use an opening
  that someone unfamiliar with the implementation can understand.
- Start with the affected workflow or behavior: what happens today, why that
  is a problem, and what changes for users. For a feature or cleanup, explain
  its purpose without inventing a failure or user benefit. Use a concrete
  example when it makes the change easier to understand.
- Give enough context to understand the change on first read. The goal is
  accessible explanation, not the fewest words or a fixed paragraph count.
  A subject alone is enough only when it also makes the purpose clear.
- Explain how the change addresses the problem at a high level. Leave code
  mechanics that readers can learn from the diff out of the prose unless they
  are needed to understand the behavior or assess a decision. Do not narrate
  the investigation, list discarded attempts, or add routine test reports.
- Include compatibility constraints, tradeoffs, or scope limits when they
  matter to readers. Preserve qualifications that prevent a misleading claim;
  do not turn these topics into a checklist that every message must cover.
- Apply [plain-technical-communication](../plain-technical-communication/SKILL.md):
  use common words, name the actor, and write short, direct sentences. Keep
  precise technical terms, code identifiers, conditions, and uncertainty when
  needed, and explain unfamiliar terms before relying on them. Remove filler,
  repetition, and unnecessary acronyms. Scale this to the message, without a
  separate prose-review ceremony.
- If a command, error excerpt, or validation result is essential to explain
  the problem or support a claim, include it briefly and concretely. Do not
  leave placeholders such as `<probe>` or `<failure log>` in the final text.
- When citing upstream commits to explain when behavior changed, pair the hash
  with a stable release version when that gives the reader a better sense of
  time.
- Insert one blank line after the subject when a body or trailers follow.
  Wrap prose to 72 columns. Before finalizing a permanent commit message, use
  `scripts/format_commit_message.py` instead of manually reflowing long
  paragraphs.
- If the repository context does not reveal the why, flag the missing context
  outside the draft instead of fabricating a justification.
- Do not turn the commit body into a PR template. Avoid Markdown headings such
  as `Summary`, `Testing`, or `Checklist` in the permanent message unless the
  user explicitly asks for that format.

### Protect identifying information in permanent and public text

- Never include user, customer, or organization-identifying information in a
  commit message, PR title, or PR description unless the user explicitly
  directs you to publish that specific identity.
- Generalize private incident context to the technical symptom, such as "an
  image push" or "a deployment". Remove names, email addresses, account or
  tenant names, private invocation IDs, hostnames, internal repository names,
  and similar attribution when they are not essential to the public change.
- Information appearing in a prompt, log, browser page, branch, or local file
  is context, not authorization to publish it. Before committing or updating a
  PR, scan the final title and body for identifiers that came from non-public
  incident evidence.

5. Preserve or supply trailers correctly.

- Keep existing trailers such as `Signed-off-by:` unchanged.
- If the user mentions `git commit -s`, do not remove the sign-off trailer.

6. Handle single-patch submissions as self-contained units.

- Make a single-patch commit message understandable without the chat history.
  Do not repeat it in a separate PR narrative unless extra context is needed.
- Keep the permanent commit message readable as plain text. If the user wants
  long logs, many links, or reviewer-only reference material, prefer a short
  appendix below `---` or move that material into the PR body.
- If extra reviewer-only context is needed for emailed patches, put it below
  `---` rather than in the permanent commit message body.

## Output

- Return the final commit message in a fenced `text` block unless the user
  explicitly asks for a different format.
- For PR metadata, derive the title and body from the same subject and body.
  Keep claims synchronized. Respect required PR templates, but do not expand
  the description just because GitHub permits more space or copy its headings
  into the permanent commit message.
- Return the requested draft without a preamble, checklist, or explanation of
  the drafting process. Honor the user's requested length and format.
- When confidence is low, add one short sentence after the block describing
  the missing context.
- When reviewing an existing message, list the concrete violations first and
  then provide a corrected version.

## Quick Checks

- Subject is 50 characters or fewer.
- Subject starts with a repo-appropriate component prefix.
- Subject uses imperative mood.
- Line 2 is blank when a body or trailers follow.
- Body prose stays within 72 columns; structured text remains unchanged.
- A reader unfamiliar with the implementation can understand the affected
  behavior, purpose, and expected change without reading the diff first.
- Body explains the approach at a high level; it does not repeat code mechanics
  or narrate the investigation.
- Detail helps readers understand the change or assess its limits, rather than
  merely making the message longer. Necessary qualifications remain intact.
- Prose uses common words and short, direct sentences, not a GitHub template.
- Any embedded commands or log excerpts are concrete and brief, not
  placeholders.
- Commit and PR text contains no user, customer, or organization-identifying
  information unless publication of that exact identity was explicitly
  requested.
- If upstream commits are cited for timing context, release/version context is
  included when it materially helps orientation.
- If validation warns that the body lacks why/context, check whether the
  actual problem and motivation are clear. Revise missing context, not wording
  that is already clear merely to satisfy the keyword heuristic.
- Trailers are preserved.

## Resources

- Read [git-my-first-contribution.md](references/git-my-first-contribution.md)
  for the distilled guidance that this skill follows.
- Run `scripts/format_commit_message.py` after drafting a commit message and
  before validation. It uses `fmt` for prose while preserving the subject,
  trailers, comments, quotes, indented text, fenced blocks, and reviewer-only
  text below `---`.
- Run `scripts/validate_commit_message.py` when the user asks to validate an
  existing commit message, when drafting a final message for commit/squash
  workflows, or when a draft is close to the line-length limits.
- Treat validator `WARN` output as a prompt to review the message. Its
  why/context check matches a small keyword list, so a warning can be a false
  positive; do not add filler solely to silence it. A missing-body warning is
  acceptable when the subject alone explains the change sufficiently.

```bash
python3 scripts/format_commit_message.py --write .git/COMMIT_EDITMSG
python3 scripts/validate_commit_message.py .git/COMMIT_EDITMSG
formatted_message="$(printf '%s\n' "$message" \
  | python3 scripts/format_commit_message.py -)"
printf '%s\n' "$formatted_message" \
  | python3 scripts/validate_commit_message.py -
```
