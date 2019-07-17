# DotFiles

Son Luong's configuration files for a Linux(Ubuntu 19.04) environment

**This project is a WIP**

## Installation

Using [init.sh](./init.sh) is a quick way to get all the config files cloned and bootstrapped
```shell
curl -s https://raw.githubusercontent.com/sluongng/dotfiles/master/init.sh | sh
```


One quick way to check content of this project after
```shell
# Navigate to cloned folder
cd ~/.dotfiles

# Run tree with (show all files) and (ignoring .git folder)
tree -I .git -a
```

## Goals

- [X] Backup most dotfiles

- [X] Security sanitization

- [X] Create migration script(bash or make) to apply these dotfiles quickly

- [ ] Create Dockerfile to host remote dev environment

## Components

- Automation:

  - Telegram: installation script and desktop file (for Ubuntu)

- ZSH shell:

  - Replace GNU with Rust/Golang tools

  - Language specific settings

- Tmux config

  - Selection with Vim mode

- NeoVim

  - VimPlug

    - fugitive

    - surround

    - vim-gitgutter

    - AirLine

    - FZF

    - NERDTree

    - Vim-Go

    - Coc.nvim

      - Language servers

      - Extensions

- IdeaVim: vimrc for JetBrains' IDEs (IntelliJ, GoLand,...)

- LibInput Gesture: Touch Pad swipe detection for laptop running Ubuntu

- Alacritty: Alacritty terminal emulator configuration
