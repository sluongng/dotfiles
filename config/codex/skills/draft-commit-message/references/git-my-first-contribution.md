# Git MyFirstContribution Commit Message Notes

Source:
- https://git-scm.com/docs/MyFirstContribution
- Consulted on 2026-03-25; the page reported itself as last updated in 2.52.0.

## Core structure

- Use a single-line subject with the component name, for example
  `component: summary`.
- Keep the subject at 50 characters or fewer.
- Write the subject in imperative mood, as if directing the codebase to do
  something.
- Follow the subject with a blank line.
- Put the bulk of the context in the body.
- Use the body to explain why and any context that is not obvious from the
  diff alone.
- Wrap body prose to about 72 columns.
- Preserve `Signed-off-by:` trailers when present.

## Single-patch notes

- A single-patch contribution should have a commit message that already
  explains what changed and why at a high level.
- When opening a GitHub PR for a single patch, the PR description can usually
  be left empty instead of repeating the commit message.
- When preparing an emailed patch and extra reviewer-only context is still
  needed, add that context below `---` rather than in the permanent commit
  message body.

## Example subject from the guide

- `psuh: add a built-in by popular demand`

## Adaptation rules

- Reuse the target repository's own component names when possible.
- Prefer splitting unrelated changes into separate commits over writing a vague
  umbrella subject.
