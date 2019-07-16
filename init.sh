#!/bin/bash +e

# This bash script should be executed with the assumption
#   that the provisioned instance has been equipped with all the needed tools
#
# It is so that we can use this together with instances provisioned using Docker
#   where which the tooling are installed in a separate layer and cached
#
# Assumptions:
# - Has git installed
# - Has networking tools such as curl, wget, ping, traceroute etc..
# - Has custom tools installed
#   + FZF, fd, ripgrep
#   + nvim
#   + tmux
#
# Goals:
# - Provisioned all configuration files

# Clone repo
git clone https://github.com/sluongng/dotfiles ~/.dotfiles

# Backup existing files
if [ -f "~/.zshrc" ]; then
  cp ~/.zshrc ~/.zshrc.bak
  echo 'Done back up zsh config'
fi

if [ -f "~/.vimrc" ]; then
  cp ~/.vimrc ~/.vimrc.bak
  echo 'Done back up vim config'
fi

if [ -f "~/.config/nvim/init.vim" ]; then
  cp ~/.config/nvim/init.vim ~/.config/nvim/init.vim.bak
  echo 'Done back up neovim config'
fi

if [ -f "~/.config/nvim/coc-config.json" ]; then
  cp ~/.dotfiles/.config/nvim/coc-config.json ~/.dotfiles/.config/nvim/coc-config.json.bak
  echo 'Done back up coc.nvim config'
fi

# Provisioning directories
mkdir -p ~/.config/nvim/

# Link all the dotfiles
ln -sfn ~/.dotfiles/.zshrc ~/.zshrc

ln -sfn ~/.dotfiles/.vimrc ~/.vimrc
ln -sfn ~/.dotfiles/.vimrc ~/.config/nvim/init.vim

ln -sfn ~/.dotfiles/.config/nvim/coc-config.json ~/.config/nvim/coc-config.json
