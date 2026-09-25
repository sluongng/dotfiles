# Install through the dedicated root service

Use this workflow for an authorized workstation upgrade, not an audit or
build-only request. Keep artifact preparation separate from privileged install
and runtime activation; each can succeed or be deferred independently.

## Check the exact permission

Inspect without starting the installer:

```sh
sudo -n -ll /usr/bin/systemctl start codex-stack-install.service
systemctl cat codex-stack-install.service
stat -c '%U %G %a %n' /usr/local/libexec/codex-stack-install
```

Require the exact command to match with `!authenticate` (NOPASSWD), and verify
the service and helper are root-owned and not user-writable. A failed
`sudo -n true` or general credential-cache check says nothing about this rule.
Do not add blanket passwordless sudo or unrestricted package-manager access.

## Prepare the candidate

The existing user-side updater is
`/home/nb/work/misc/desktop/maintenance/bin/codex-stack-update`; the installed
privileged helper is `/usr/local/libexec/codex-stack-install`. Read their current
implementation and repository instructions before invoking either. The updater
supports `--build-only` and `--activate-only`; activation can stop services and
rerender config, so it is not an install-only command.
Do not run its default mode or `--activate-only` while its internal restart
checks still use `--allow-single-active`. An external idle precheck does not
repair that weaker internal guard. Use build-only preparation and, where safe,
the validated install-only service; defer runtime activation until the wrapper
enforces the strict guard immediately before disruption.

Use the updater's current candidate schema under
`~/.local/state/codex-stack-update/ready/`. Bind the selected package versions,
hashes, and completed validation to the exact candidate. Do not fabricate a
`validation=passed` marker or invoke the service against an old ready pointer.

When staging a wrapper build, copy every local PKGBUILD source, including
`codex-launcher`. Preserve each source's independent checksum; updating the
DEB hash must not overwrite the launcher's hash. Verify fixes with the existing
build/validation workflow instead of bypassing a failing source check.

Review the installed helper's trust boundary as well as the user-side updater.
User-writable candidate hashes and package names alone do not authenticate
payloads. The privileged path must independently establish trusted provenance
for the payload it installs and validate local wrapper differences. Keep
executable smoke tests unprivileged. If the current helper trusts only candidate
metadata or runs candidate executables as root before authenticating them,
report that concrete blocker; do not treat the existing sudo rule as proof that
the helper is safe or claim a skill edit repaired it.

## Install and activate

After candidate validation and the helper checks pass, the authorized fixed
privileged command is:

```sh
sudo -n /usr/bin/systemctl start codex-stack-install.service
```

Before using a wrapper that stops/restarts runtimes, follow
[remote-access.md](remote-access.md). Require the strict idle guard; an updater's
`--allow-single-active` exception does not satisfy this skill's restart rule.
Do not bypass maintenance inhibitors, lock checks, or helper rejection by
switching to direct root execution. If only a restart is blocked and the
validated install-only path can preserve active work, installation may finish
while activation remains deferred. Otherwise leave the validated candidate ready.

If the fixed path is unavailable, report the exact failure and a concrete
fallback command for review. Broader root execution or changes to the privilege
bridge require separate authority; do not request installation permission again
when the real issue is a broken helper or missing OS privilege.

After installation, verify pacman versions/files, real CLI and bundled versions,
strict config health, and service/socket ownership. Report installed and running
versions separately, including old unlinked executables or Browser workers that
still need a guarded restart. Preserve whether the App was stopped; do not
enable or launch it merely because its package was upgraded.
