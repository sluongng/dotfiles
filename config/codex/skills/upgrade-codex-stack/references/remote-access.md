# Shared App-Server and Remote Access

Use this reference for every full stack upgrade and whenever the CLI, desktop
App, app-server service, SSH or Relay connection, or task ownership may change.

## Contents

- [Target topology](#target-topology)
- [Ownership audit](#ownership-audit)
- [Task-state semantics](#task-state-semantics)
- [Guarded handoff](#guarded-handoff)
- [App connection validation](#app-connection-validation)
- [Runtime version boundary](#runtime-version-boundary)
- [Acceptance matrix](#acceptance-matrix)

## Target topology

Use one authoritative shared external app-server and one shared `~/.codex`
thread store for the desktop App's machine connection, LAN SSH, and OpenAI Relay:

```text
Desktop ChatGPT App --SSH connection: <lan-ssh-alias>--------+
ChatGPT iOS --LAN SSH connection----------------------------+--> ssh ... codex app-server proxy
                                                              --> shared Unix socket
                                                              --> systemd-managed /usr/bin/codex app-server
                                                              --> shared ~/.codex thread store

ChatGPT iOS --OpenAI Relay-----------------------------------> same shared app-server and thread store

Desktop ChatGPT App --Local + local-daemon handoff-----------> same shared app-server and thread store
```

The Arch App launcher must export `CODEX_APP_SERVER_USE_LOCAL_DAEMON=1`. The
first-party Linux App recognizes this setting and connects its `Local` host to
`~/.codex/app-server-control/app-server-control.sock` when the daemon version is
compatible. The App-bundled Codex binary performs the compatibility probe and
remains the upstream fallback if the socket is missing or the daemon is too old.
After every App or CLI upgrade, prove the handoff from process and socket state;
do not infer it from the environment variable alone.

Treat
`~/.dotfiles/config/systemd/user/codex-remote-control.service` as the
authoritative service. Expect it to run:

```text
/usr/bin/codex app-server --remote-control --listen unix://
```

Do not expose an app-server listener directly to the LAN or internet. Use the
supported App SSH connection, SSH/VPN/mesh transport, or OpenAI Relay.

## Ownership audit

Begin read-only and inspect at least:

```bash
systemctl --user show codex-remote-control.service \
  -p LoadState -p ActiveState -p SubState -p UnitFileState \
  -p MainPID -p ExecStart
systemctl --user status codex-remote-control.service --no-pager
journalctl --user -u codex-remote-control.service \
  --since '15 minutes ago' --no-pager
codex app-server daemon version
ps -eo pid,ppid,lstart,args | \
  rg 'codex app-server|codex app-server proxy|ChatGPT|codex-code-mode-host'
lsof -nP -U | rg 'app-server-control\.sock'
```

Verify that the service is enabled and active, its nonzero `MainPID` is the
expected `/usr/bin/codex app-server`, and that exact process owns the shared
socket. Distinguish it from the App-bundled Local server and SSH
`codex app-server proxy` processes. `codex app-server daemon version` can prove a
server is reachable without proving that systemd owns it.

With the desktop App running, also verify that the launcher environment contains
`CODEX_APP_SERVER_USE_LOCAL_DAEMON=1` and that there is no persistent child such
as `/usr/lib/chatgpt/resources/codex ... app-server`. A short-lived bundled
`app-server daemon version` probe is expected during startup; a persistent
bundled app-server means the handoff fell back and can recreate writer conflicts.

## Task-state semantics

Record task ownership before any restart. Distinguish:

- **active:** a turn is running or a client is actively controlling the task;
  do not take ownership away;
- **idle but loaded:** the turn has ended, but the server may retain ownership
  for an unload timeout;
- **not loaded:** a normal dormant task state, not evidence of missing or
  corrupted history;
- **open in another app:** normally writer ownership contention, not by itself
  an SSH, authentication, PATH, or rollout-integrity failure.

An idle remote task may remain loaded after its client unsubscribes. Prefer
waiting for normal unload. If immediate release is necessary, restart the shared
server only after proving that no remote turn is active and the user has
authorized the disruption.

## Guarded handoff

When an authorized CLI upgrade or restart requires an ownership handoff:

1. Inventory active turns, SSH proxies, relay state, the exact socket owner, its
   executable, parent process, and cgroup.
2. Do not interrupt the server while a remote turn is active.
3. If `codex app-server daemon stop` reports that the server is not managed, do
   not retry it blindly. Resolve the exact unmanaged PID and confirm that it owns
   the shared socket.
4. Gracefully terminate only that exact process after active work is clear.
5. Start or restart `codex-remote-control.service` as authorized.
6. Verify that the service's new `MainPID` owns the socket and that no second
   authoritative external server remains.
7. Inspect the journal until OpenAI Relay reaches an affirmative connected state.
8. Reconnect the App's machine-local SSH connection and verify that its proxy
   attaches to the existing shared socket.
9. Verify task state through the app-server API and the visible App UI before
   declaring the handoff successful.

A relay `409 Conflict` or `Remote app server already online` can be transient
during replacement. Check local socket health separately, look for another live
server, and wait with bounded backoff for a connected journal event. Do not use
an extra long-lived `codex remote-control --json` process as the sole health
probe because it can itself establish or compete for relay ownership.

Never recover ownership by editing `state_5.sqlite`, the App's LevelDB, or
`app.asar`; deleting lock files without proving they are stale; starting another
server before identifying the socket owner; or broadly killing Codex processes.
Use supported app-server, systemd, App Settings, and connection flows.

## App connection validation

Create or repair the machine-local SSH connection only through the desktop App
**Settings > Connections > SSH** flow or a supported App deep link. Never insert
connection records directly into App storage. After an App update or restart,
verify that:

- the saved connection still exists and authenticates without an interactive
  password prompt;
- a live `ssh ... <lan-ssh-alias> ... codex app-server proxy` process reaches
  the shared server;
- the connection becomes connected and auto-connect behavior survives a real
  App restart;
- a dormant shared task can be opened through the SSH-backed host;
- the same task remains available through OpenAI Relay;
- the task is not simultaneously resumed through both `Local` and the remote
  host.

Separate backend visibility from client presentation. `thread/list` or another
API may return a remote task even when the App connection sidebar does not show
historical tasks, and a generic task deep link may choose `Local` when the same
task ID exists on multiple hosts. Report each layer separately:

1. shared app-server can list and read the task;
2. App connection backend reports it;
3. desktop connection sidebar visibly lists and opens it;
4. iOS SSH connection visibly lists and continues it;
5. iOS Relay connection visibly lists and continues it.

Do not repair a client listing or host-selection limitation by mutating its
database. Actual-device iOS verification is a separate acceptance test; local
server evidence cannot prove the iOS connection picker or task list works.

## Runtime version boundary

Record the version boundary rather than treating every difference as a conflict:

| Responsibility | Expected runtime |
| --- | --- |
| Interactive CLI and shared app-server | `/usr/bin/codex` from the Arch CLI package |
| SSH proxy backend | The same system CLI and shared socket |
| Desktop App Local host | Shared system app-server socket via `CODEX_APP_SERVER_USE_LOCAL_DAEMON=1` |
| Desktop Local compatibility probe/fallback | App-bundled Codex under `/usr/lib/chatgpt/resources/` |
| Desktop code mode | App-bundled `codex-code-mode-host` |
| Desktop Browser/JavaScript MCP | App-bundled native runtime and `node_repl` |

System CLI and App-bundled versions may legitimately differ. Require a working
protocol handshake and compatible configured paths; do not require equal version
strings unless upstream documents that constraint.

## Acceptance matrix

Mark each row pass, fail, not tested, or not applicable:

| Scenario | Required result |
| --- | --- |
| System service | Enabled and active; `MainPID` owns the shared socket |
| LAN SSH | The machine-local alias authenticates and finds the expected system CLI |
| SSH proxy | Attaches to the shared socket without starting another owner |
| OpenAI Relay | Reaches a connected state after any bounded takeover period |
| Desktop App Local | Reuses the shared socket; no persistent bundled app-server |
| Desktop App SSH | Connects and opens a dormant shared task |
| Task handoff | Releases and reacquires ownership without database mutation |
| Concurrent resume | Avoided or rejected; never report it as a supported dual-writer path |
| App restart | Saved SSH connection and auto-connect behavior are verified |
| iOS SSH | Task listing and continuation are verified on the device |
| iOS Relay | The same shared task listing and continuation are verified on the device |
| Version boundary | System CLI, shared server, App bundle, and code-mode versions are recorded |
