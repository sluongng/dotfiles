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

## Terminal sessions

The default interactive stack is `Ghostty -> tmux -> zsh / Neovim / Codex /
agy`. A local top-level terminal creates or attaches to the persistent `main`
tmux session automatically. SSH shells, detected Emacs, Vim, IntelliJ, and Zed
terminals, existing tmux panes, and manually started Herdr panes are not nested.
Set `TMUX_AUTOSTART=0` before starting zsh for an ordinary shell outside tmux.

Herdr remains installed and available manually with `herdr`, but it is no
longer started by the shell. Its tracked config retains the same primary
workflow:

- `Ctrl-a c`: new tab
- `Ctrl-a l` / `Ctrl-a j`: split right / down
- `Ctrl-a` plus an arrow: move between panes
- `Ctrl-a o`: cycle to the next pane
- `Ctrl-a F`: find a workspace, tab, pane, or agent
- `Ctrl-a [`: vi-style copy mode
- `Ctrl-a f`: copy a visible token with Herdr Pluck
- `Ctrl-a u`: open a visible URL with Herdr Pluck
- `Ctrl-a q`: detach while keeping processes alive

`init.sh` still installs Herdr's first-party Codex and Antigravity CLI hooks
when the corresponding config directories exist. Check them with
`herdr integration status`. The Herdr Pluck plugin remains Herdr-managed and
can be installed with `herdr plugin install rmarganti/herdr-pluck --yes`.

## Neovim

The shared Neovim configuration uses `vim.pack` and the current
`nvim-treesitter` `main` branch on both macOS and Linux. It requires Neovim
0.12 or newer, Git, `curl`, `tar`, a C compiler, and `tree-sitter` CLI 0.26.1
or newer. The Brewfile supplies the macOS dependencies; Linux packages remain
host-managed.

Run `:PackUpdate!` to update plugins and synchronize all configured Tree-sitter
parsers. The optional local Tree-sitter grammar checkout does not affect the
portable plugin lockfile:

```sh
export NVIM_TREE_SITTER_BAZELRC_PATH=~/work/misc/tree-sitter-bazelrc
```
