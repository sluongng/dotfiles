# Validate the Integrated Result

Repeat version and configuration checks against the newly built artifacts. Confirm that:

- package metadata, contents, and embedded versions agree;
- the desktop artifact came from the selected first-party or fallback channel,
  and its signature/checksum evidence is recorded;
- the desktop package passes its smoke and relevant runtime tests;
- a first-party payload remains unmodified unless a documented compatibility
  failure required a narrowly scoped patch;
- the Arch package does not depend on executing Debian or RPM maintainer scripts;
- first-party and legacy desktop entries, profiles, and URL handlers have an
  explicit coexistence or migration plan;
- source config renders consistently or documented local overlays explain the difference;
- feature recommendations match the target binary rather than only upstream main;
- the systemd-managed `MainPID` owns the shared app-server socket, or any
  intentional deviation is explained;
- the desktop App's `Local` connection reuses the shared daemon and does not
  leave a persistent App-bundled app-server process;
- LAN SSH and the App's SSH connection attach through `codex app-server proxy`
  without starting a competing authoritative server;
- OpenAI Relay reaches a connected state after any transient takeover period;
- a dormant shared task can be listed, read, and opened through the intended
  host without concurrent Local/remote writer ownership;
- desktop and iOS UI visibility are reported separately from API visibility,
  with unperformed actual-device checks labeled as such;
- an authorized App restart preserves or reconnects the saved SSH connection;
- no unrelated dirty files were overwritten;
- no required install or restart was silently performed.

For an upgrade that changes the CLI, desktop App, app-server service, or
connection state, include the matrix from
[references/remote-access.md](remote-access.md) and mark each row
pass, fail, not tested, or not applicable.

On Hyprland, add a lightweight post-upgrade smoke check for the main window,
right-click menus and popovers, pet placement/workspace following, unexpected
focus activation, and compositor configuration errors. Route failures to the
`desktop-incident-triage` skill; do not turn this package-upgrade workflow into a
compositor repair or patch the vendor payload for a window-management symptom.

Do not call the run complete when a required build, smoke test, or configuration check failed. State the blocker, preserve useful artifacts, and give the smallest recovery step.
