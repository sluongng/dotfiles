# Upgrade and Validate the Linux Desktop App

Always include `/home/nb/work/misc/codex-app` in a full run. Follow its repository
instructions and existing scripts. Evolve that repository's packaging path when
the user requests an upgrade; do not build a one-off package outside it.

### Prefer the first-party Linux package

1. Discover the current `.deb` or `.rpm` from an official OpenAI page or signed
   package repository. Select the host architecture explicitly.
2. Verify signed repository metadata and then verify the downloaded artifact
   against its exact size and SHA-256. Record the signing-key fingerprint from
   the verified metadata; allow legitimate key rotation instead of hardcoding a
   historical fingerprint as permanent truth. State precisely whether trust
   comes from signed repository metadata authenticating the package hash, a
   per-package signature, or both; do not describe an unsigned `.deb` as
   directly signed.
3. Inspect package metadata, file layout, dependencies, desktop/MIME handlers,
   AppArmor policy, and maintainer scripts before building or installing
   anything. Treat maintainer scripts as untrusted-to-run during inspection.
4. On Arch/CachyOS, never install the `.deb` with `dpkg`, add its APT repository,
   or execute its maintainer scripts. Use the repository's Arch-native wrapper
   for the official payload. If none exists and the user requested an upgrade,
   add the smallest maintainable wrapper to that repository rather than
   extending the legacy macOS conversion path.
5. Preserve the vendor application payload and native runtimes byte-for-byte
   unless a concrete host incompatibility proves a patch is necessary. Keep the
   first-party layout and names, including the unified ChatGPT branding, rather
   than rewriting them to resemble the legacy package. Treat vendor binaries and
   resources as the immutable payload boundary; Arch package metadata, launchers,
   and host-integration files may differ when necessary and must be reviewed
   explicitly.
6. Build a pacman-inspectable artifact and check package ownership, conflicts,
   upgrade behavior, desktop entry, URL scheme, MIME registration, and any
   coexistence rules with the legacy installation.

Validate the first-party payload before activation using isolated `HOME`,
`CODEX_HOME`, and XDG directories. At minimum check:

- package signature provenance, checksum, architecture, ELF types, and unresolved
  shared libraries;
- renderer startup and the bundled app-server initialization handshake;
- bundled `codex --version`, `codex-code-mode-host`, and `rg`;
- `node_repl` MCP initialization, tool listing, JavaScript evaluation, and the
  Browser bridge;
- clean process shutdown and absence of probe processes afterward.

Do not interpret an isolated probe's missing login or failed `codex://`
registration as a product failure. Those require an installed desktop session.
Do not copy browser cookies, app credentials, or authentication state between
profiles; use the application's supported sign-in flow when installation is
authorized.

### Use the legacy repackager only as fallback

If the first-party Linux release cannot be used, resolve the macOS target with
`npm run release-info -- --json` or the current equivalent and use the existing
forced repackage, install, and smoke-test commands. Patch only concrete bundle
drift or Linux compatibility failures. For this path, continue verifying the
pinned Linux `node_repl`, manifest/checksum, GLIBC compatibility, Browser
native-pipe behavior, and required compatibility patches. Refresh checked-in
fixtures only when their source bundle changed.

Keep the runtime boundary explicit in the report: the desktop app's `node_repl`
serves Browser/JavaScript MCP, while CLI code mode uses
`codex-code-mode-host`. The first-party package should supply native Linux builds
of both; the legacy path may source them separately.

An upgrade request authorizes updating the existing App package through
[installation.md](installation.md), with runtime restarts subject to the strict
idle guard. It does not authorize switching distributions or migrating profiles.
For a separately authorized migration, prefer a side-by-side first-party installation and distinct
profile for initial parity testing only after checking app IDs, single-instance
locks, DBus names, URL/MIME handlers, and profile paths for collisions. If those
cannot be isolated, use an extracted-package probe instead of simultaneous
activation. Report the generated Arch artifact, the channel used, installation
and activation results, and any deferred commands verified from the repository
or package metadata.
