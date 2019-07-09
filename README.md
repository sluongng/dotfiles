# DotFiles

Son Luong's configuration files for a Linux(Ubuntu 19.04) environment

**This project is a WIP**

## Goals

- [ ] Backup most dotfiles

- [ ] Security sanitization

- [ ] Create migration script(bash or make) to apply these dotfiles quickly

- [ ] Create Dockerfile to host remote dev environment

## Components

- ZSH shell:
  - Replace GNU with Rust/Golang tools
	- Language specific settings

- Tmux config:
  - Selection with Vim mode

- NeoVim:
	- VimPlug:
		- fugitive
		- surround
		- vim-gitgutter
		- AirLine
		- FZF
		- NERDTree
	  - Vim-Go
		- Coc.nvim: 
			- Language servers 
			- Extensions

- IdeaVim: vimrc for JetBrains' IDEs (IntelliJ, GoLand,...)

- LibInput Gesture: Touch Pad swipe detection for laptop running Ubuntu

- Alacritty: Alacritty terminal emulator configuration
