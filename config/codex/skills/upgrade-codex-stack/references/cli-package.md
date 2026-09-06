# Upgrade the Arch CLI Package

Work with the existing `PKGBUILD`; do not replace its packaging design. Preserve user modifications and the `/usr/lib/openai-codex` layout unless upstream now requires a justified migration.

1. Update `pkgver`, sources, asset names, and checksums for the selected alpha.
2. Preserve Arch alpha version ordering, converting upstream separators only as required by pacman version syntax.
3. Refresh `.SRCINFO` from `makepkg --printsrcinfo`.
4. Verify that the package still installs the primary binary and expected helpers, including `codex-code-mode-host`, sandbox support, `rg`, `zsh`, and the responses API proxy when present in the established package.
5. Do not add the desktop `node_repl` runtime to this package solely because CLI code mode exists. CLI code mode uses `codex-code-mode-host`; add another runtime only after finding a real CLI consumer and an upstream path contract.

Run proportionate packaging validation:

```bash
makepkg --verifysource
makepkg -Ccf
diff -u .SRCINFO <(makepkg --printsrcinfo)
pacman -Qip ./<package-file>
pacman -Qlp ./<package-file>
```

Extract the built package into a temporary directory, run its embedded `codex --version`, and inspect helper binary types. Report the exact artifact path, version, package layout result, and deferred `sudo pacman -U ...` command.
