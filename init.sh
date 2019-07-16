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
if [ ! -d "~/.dotfiles" ]; then
  git clone git@github.com:sluongng/dotfiles.git ~/.dotfiles
else 
  echo 'Directory .dotfiles already exist, pulling instead of cloning'
  git -C ~/.dotfiles pull
fi

# Backup existing files
if [ -f "~/.zshrc" ]; then
  cp ~/.zshrc ~/.zshrc.bak
  echo 'Done back up zsh config'
else
  echo 'No .zshrc found'
fi

if [ -f "~/.vimrc" ]; then
  cp ~/.vimrc ~/.vimrc.bak
  echo 'Done back up vim config'
else
  echo 'No .vimrc found'
fi

if [ -f "~/config/nvim/init.vim" ]; then
  cp ~/config/nvim/init.vim ~/.config/nvim/init.vim.bak
  echo 'Done back up neovim config'
else
  echo 'No init.vim(neovim config) found'
fi

if [ -f "~/config/nvim/coc-config.json" ]; then
  cp ~/.dotfiles/config/nvim/coc-config.json ~/.dotfiles/.config/nvim/coc-config.json.bak
  echo 'Done back up coc.nvim config'
else
  echo 'No coc-config.json(coc.nvim config) found'
fi

if [ -f "~/.tmux.conf" ]; then
  cp ~/.tmux.conf ~/.tmux.conf.bak
  echo 'Done back up tmux config'
else
  echo 'No .tmux.conf(tmux config) found'
fi

# Provisioning directories
mkdir -p ~/config/nvim/

# Link all the dotfiles
ln -sfn ~/.dotfiles/.zshrc ~/.zshrc
echo 'Linked .zshrc from dotfiles'

ln -sfn ~/.dotfiles/.vimrc ~/.vimrc
ln -sfn ~/.dotfiles/.vimrc ~/config/nvim/init.vim
echo 'Linked .vimrc from dotfiles'

ln -sfn ~/.dotfiles/config/nvim/coc-config.json ~/.config/nvim/coc-config.json
echo 'Linked coc-config.json from dotfiles'

ln -sfn ~/.dotfiles/.tmux.conf ~/.tmux.conf
echo 'Linked .tmux.conf from dotfiles'
