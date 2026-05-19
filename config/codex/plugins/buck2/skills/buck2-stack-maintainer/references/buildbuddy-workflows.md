# BuildBuddy Workflows

Buck2 uses `buildbuddy.yaml` at the repository root. The intended action name
is `Buck2 Stack Test`.

The action is intentionally API/manual-dispatch driven (`triggers: {}`) so the
maintainer can push prefix merge commits without also causing duplicate webhook
runs. Start and poll the workflow with the public API:

```bash
python3 scripts/buildbuddy_workflow.py \
  --repo-url https://github.com/sluongng/buck2 \
  --branch main \
  --commit-sha <merge-commit-sha> \
  --action-name "Buck2 Stack Test" \
  --poll
```

Before rewriting `fork/main`, run the setup check mode. It verifies the current
merge-parent invariant and performs the same workflow preflight without a
rebase, merge, or push:

```bash
python3 scripts/sync_stack.py --check-buildbuddy-setup
```

Use `--attempt-buildbuddy-link` with the setup check in unattended runs. When
the preflight sees BuildBuddy's `repo ... not found` setup error, the script
runs `buildbuddy_link_repo_browser.py` once and retries the preflight. This is
still fail-closed: if the GitHub App installation does not expose the repo, the
link helper returns the accessible repo list and the sync stops before any
branch rewrite.

The helper reads the API key from `BUILDBUDDY_API_KEY` by default, falling back
to `[buildbuddy] api_key = ...` in `.buckconfig.local`, and sends it as the
`x-buildbuddy-api-key` header. Keep the key out of logs.

If the API returns `repo "https://github.com/sluongng/buck2" not found`, the
BuildBuddy GitHub App or Workflow setup is not enabled for the fork yet. Stop
and enable Workflows for `sluongng/buck2`; do not keep force-pushing while the
repo is unknown to BuildBuddy.

For the current fork setup, the GitHub-side prerequisite is that the existing
BuildBuddy GitHub App installation for the `sluongng` account includes the
`sluongng/buck2` repository:

- GitHub app installation URL: `https://github.com/settings/installations/36994646`
- GitHub repository id: `634428231`
- BuildBuddy org to link from: `Son Luong Ngoc`
- BuildBuddy link page: `https://app.buildbuddy.io/workflows/new`

If GitHub asks for sudo-mode re-authentication, a human must complete it before
the maintainer can link or trigger the workflow. The local `gh` OAuth token is
not enough for this app-installation edit.

The GitHub-side prerequisite helper verifies the fork repository id and prints
the exact app-installation and BuildBuddy link URLs:

```bash
python3 scripts/github_app_prereq.py
```

If the currently configured `gh` auth is able to modify the app installation,
this can also attempt the desired repository grant:

```bash
python3 scripts/github_app_prereq.py --attempt-add
```

After GitHub App access exists, link the repository in the logged-in
BuildBuddy org without clicking through the UI:

```bash
python3 scripts/buildbuddy_link_repo_browser.py
```

This helper uses the local Codex Chrome bridge against the logged-in
BuildBuddy page, selects the `Son Luong Ngoc` group, verifies that the GitHub
App installation exposes `https://github.com/sluongng/buck2`, and then calls
BuildBuddy's `linkGitHubRepo` RPC.

Useful API details:

- Execute endpoint: `https://app.buildbuddy.io/api/v1/ExecuteWorkflow`
- Poll endpoint: `https://app.buildbuddy.io/api/v1/GetInvocation`
- `ExecuteWorkflow` request fields used here:
  `repo_url`, `branch`, `commit_sha`, `action_names`, `async`, and `env`.
- BuildBuddy fetches `buildbuddy.yaml` from `commit_sha`, so
  `sync_stack.py` overlays the workflow harness files from the stack tip onto
  each temporary prefix merge commit before triggering this API.
- A workflow invocation is done when `invocationStatus` is
  `COMPLETE_INVOCATION_STATUS`; then `success` determines pass/fail.
