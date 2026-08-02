# Dotfiles

Shared configuration for macOS and Linux development machines.

## Install

On a new machine:

```sh
curl -fsSL https://raw.githubusercontent.com/sluongng/dotfiles/master/init.sh | bash
```

From an existing checkout:

```sh
./init.sh
```

The bootstrap is safe to rerun. It links common shell, terminal, editor, Git,
and Codex configuration, then installs every tracked Codex skill. Files that
would be replaced are moved under `~/.dotfiles-backups/<timestamp>/`.

The platform-specific split is deliberate:

- macOS installs Karabiner configuration.
- Linux installs Hyprland, Waybar, Mako, systemd user, and libinput gesture
  configuration.
- Package installation is not performed by default. Set
  `DOTFILES_INSTALL_PACKAGES=1` to run the macOS Brewfile; Linux packages remain
  host-managed.
- Mail configuration is opt-in with `DOTFILES_INSTALL_MAIL=1`.
- Existing checkouts are not pulled implicitly. Set `DOTFILES_UPDATE=1` to use
  `git pull --ff-only` before provisioning.

Useful overrides:

```sh
DOTFILES_DIR=/path/to/checkout ./init.sh
XDG_CONFIG_HOME=/path/to/config ./init.sh
CODEX_HOME=/path/to/codex-home ./init.sh
```

Local secrets, Codex state, Git credentials, and machine-specific project trust
entries are intentionally kept outside this repository.
