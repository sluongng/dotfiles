# Establish the Baseline and Target Releases

Record the current state before changing anything:

- installed and packaged Codex CLI versions;
- running CLI, app-server daemon, and service versions;
- current package source URLs and checksums;
- current desktop app version, installation path, distribution channel
  (first-party Linux or legacy macOS-derived), and packaged output;
- the binary and version serving each path: the interactive system CLI, shared
  app-server, desktop App Local host, SSH proxy backend, code-mode host, and
  Browser/JavaScript MCP runtime;
- shared app-server socket ownership, systemd service state, OpenAI Relay state,
  saved App SSH connections, and any active or idle loaded remote tasks;
- relevant repository commits, branches, dirty files, and upstream remotes;
- enabled/default feature flags and plugin state.

Select the latest packageable CLI alpha by checking both the npm registry metadata for `@openai/codex` and the matching official GitHub release. Do not select a tag merely because it sorts newest. Require the release assets consumed by the package, including the Linux musl CLI package and responses API proxy. If the newest alpha lacks required assets, choose the newest complete alpha and explain the gap.

Determine the desktop app target from current official Linux release metadata and
artifacts. Use the official product/download page and signed APT or RPM repository
metadata as primary evidence. Record the release date, package version,
architecture, artifact URL, size, checksum, signing identity, supported distro
matrix, and the version of the embedded Codex CLI. Do not infer freshness from a
redirect filename or compare desktop and CLI versions as if they shared a release
line.

Prefer the newest verifiable first-party Linux package. Use the macOS appcast via
the repository's `release-info` command only when auditing the legacy fallback or
when the first-party package is missing, unverifiable, or unusable. If falling
back, state the exact reason and compare both channels' versions and release
dates.
