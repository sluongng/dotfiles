# Codex App Backend on Non-Linux Hosts

Use the available Codex App automation capability on supported non-Linux hosts.
This does not supersede Linux Aton ownership. If the App capability is absent,
report the missing capability rather than fabricating a schedule or installing
systemd emulation.

Inspect existing App records and use the available automation tool to create or
update the resolved ID. App definitions/memory normally live under
`${CODEX_HOME:-$HOME/.codex}/automations/<id>/`; do not hand-edit installed App
records. Use a heartbeat for a requested conversation follow-up and the supported
recurring task mode for detached work, according to the available tool schema.

Use suggested/proposal modes only for a review-first request. Preserve account,
external-write, and duplicate-scheduler boundaries. Do not activate another copy
of a workload until its previous owner is paused and has no active run. Verify
stored schedule, status, project/cwd, and notification policy after a mutation.

App runs use `$automation-runner` with their App memory path and the output
contract required by that runtime. App inbox directives are not an Aton output
requirement.
