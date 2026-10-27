# Dotfiles Repository Guidance

## Git workflow

- Work directly on `master` and commit changes there. Do not create task
  branches unless the user explicitly requests one.
- If concurrent changes cause divergence or conflicts, fetch the latest
  `origin/master`, rebase the local commits onto it, and resolve conflicts while
  preserving both sets of intended changes. Use rebase rather than a merge
  commit to reconcile the histories.
