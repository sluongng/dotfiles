# Codex profiles

The installer copies `*.config.toml` beside `~/.codex/config.toml`. Current CLI
profiles are full configuration layers selected with `--profile NAME`.

| Command | Experiment |
| --- | --- |
| `codex --profile sol-notes` | Explicit notes/history mode with mixed-model delegation; also the shared default |
| `codex --profile sol-classic` | Ordinary summary compaction for comparison or rollback |
| `codex --profile sol-quick` | GPT-6.1 Sol/medium reasoning for routine work |
| `codex --profile sol-priority` | GPT-6.1 Sol/high on the advertised priority tier, with increased usage |
| `codex --profile sol` | GPT-6.1 Sol/medium for routine coding and agentic work |
| `codex --profile luna` | GPT-6 Luna/high for focused, bounded work |

The September 30 model refresh uses GPT-6.1 Sol/high as the interactive default.
All prior GPT-6 Astra/Sol roles and profiles now use GPT-6.1 Sol at their existing
reasoning effort; `scout` remains GPT-6 Luna/high. The former `astra-*` profiles
are now named `sol-*`. Model context limits stay at catalog defaults.

Ordinary `codex` uses GPT-6.1 Sol/high and mixed-model delegation with experimental
context management enabled. On 2026-09-05, an actual Astra parent spawned
GPT-5.6 Luna/high, Terra/medium, and Sol/high roles with the feature enabled. All three
completed a read-only calculation, recalled the result in a follow-up, wrote
and read an exact marker through native notes, and listed their history windows
without errors. Their saved states contained the new context-window guidance.

That catalog supplied token-budget prompts for all four models. Explicit
opt-in uses those defaults even though automatic activation is off. There is no
automatic fallback to summary compaction for older models: context reset is
selected whenever the token-budget feature is enabled. Role configuration in
CLI 0.154.0-alpha.3 cannot disable it individually. The earlier single-agent
restriction was removed after these compatibility checks and user clarification.
Activation is fixed at thread startup.
Start fresh tasks for comparisons rather than resuming an old thread.

Assess notes on a real task spanning context windows: retained constraints,
repeated investigation, correction frequency, completion quality, elapsed time,
and usage. These checks establish short-task and native-tool compatibility,
not reliable autonomous recovery across a context reset or reduced usage.

Keep context-window size, compaction thresholds, and tool-output limits at model
defaults during this experiment. Change one variable at a time. Use the quick
profile on comparable routine tasks before considering a global effort change.

Sources: [Gabriel Chua's instructions](https://x.com/gabrielchua/status/2096097155048223221)
and the [OpenAI configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference).
