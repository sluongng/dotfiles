# Machine-local Git configuration

The shared config includes `~/.config/git/config.local` so credentials can use
the helper available on each host without putting OS-specific paths or secrets
in dotfiles.

For Git Credential Manager on Linux:

```ini
[credential]
    helper = manager
```

For the macOS keychain helper:

```ini
[credential]
    helper = osxkeychain
```

GitHub CLI authentication also works without adding a shared credential helper.
