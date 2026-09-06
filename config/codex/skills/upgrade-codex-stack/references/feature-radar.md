# Produce a Current Feature Radar

Use the `$openai-docs` skill to consult the current official Codex and desktop-app
documentation. Documentation lookup is read-only and remains required during an
audit-only run; skip it only when the helper or upstream source is unavailable,
and report the exact freshness limitation. For a new Linux preview, cross-check
the official announcement, support matrix, product/download page, and signed
package repository because general desktop documentation may lag the release.
Also inspect the target release notes, source at the target tag, changes since the
previously installed or packaged version, and `codex features list`.

Cover practical user-facing changes in all relevant maturity classes:

- stable or newly default-enabled;
- experimental or opt-in;
- under development or source-visible but not yet supported;
- newly deprecated, renamed, or removed.

For each material feature, report:

1. maturity and availability in the target release;
2. upstream default state;
3. whether it is enabled or configured on this machine;
4. what changed since the prior version;
5. practical impact for this user's workflows;
6. a concrete way to test it;
7. whether a dotfiles change is required, recommended, optional, or unnecessary.

Distinguish shipped behavior from source-only work and supported features from experiments. Focus on material deltas rather than listing every unchanged flag. Explicitly check code mode and its host, multi-agent behavior, tool permissions, plugins and MCP, Browser/computer-use paths, memory/context behavior, TUI/app-server/remote-control behavior, and any feature family changed by the target release.

If current documentation, release metadata, or an upstream service is unavailable, continue with verified local artifacts where possible and label the freshness limitation. Never present an inference as a confirmed release fact.
