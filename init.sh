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

DIR_DOTFILE=~/.dotfiles
DIR_HOME=${HOME}
DIR_CONFIG=${DIR_HOME}/.config


# Clone repo
if [ ! -d "${DIR_HOME}/.dotfiles" ]; then
  git clone git@github.com:sluongng/dotfiles.git ${DIR_DOTFILE}
else 
  echo 'Directory .dotfiles already exist, pulling instead of cloning'
  git -C ${DIR_HOME}/.dotfiles pull
  exit 0
fi

# Backup existing files
if [ -f "${DIR_HOME}/.zshrc" ]; then
  cp ${DIR_HOME}/.zshrc ${DIR_HOME}/.zshrc.bak
  echo 'Done back up zsh config'
else
  echo 'No .zshrc found'
fi

if [ -f "${DIR_HOME}/.vimrc" ]; then
  cp ${DIR_HOME}/.vimrc ${DIR_HOME}/.vimrc.bak
  echo 'Done back up vim config'
else
  echo 'No .vimrc found'
fi

if [ -f "${DIR_CONFIG}/nvim/init.vim" ]; then
  cp ${DIR_CONFIG}/nvim/init.vim ${DIR_CONFIG}/nvim/init.vim.bak
  echo 'Done back up neovim config'
else
  echo 'No init.vim(neovim config) found'
fi

if [ -f "${DIR_CONFIG}/nvim/coc-settings.json" ]; then
  cp ${DIR_CONFIG}/nvim/coc-settings.json ${DIR_CONFIG}/nvim/coc-settings.json.bak
  echo 'Done back up coc.nvim config'
else
  echo 'No coc-config.json(coc.nvim config) found'
fi

if [ -f "${DIR_HOME}/.tmux.conf" ]; then
  cp ${DIR_HOME}/.tmux.conf ${DIR_HOME}/.tmux.conf.bak
  echo 'Done back up tmux config'
else
  echo 'No .tmux.conf(tmux config) found'
fi

# Provisioning directories
mkdir -p ${DIR_CONFIG}/nvim/

# Link all the dotfiles
ln -sfn ${DIR_DOTFILE}/.zshrc ${DIR_HOME}/.zshrc
echo 'Linked .zshrc from dotfiles'

ln -sfn ${DIR_DOTFILE}/.vimrc ${DIR_HOME}/.vimrc
ln -sfn ${DIR_DOTFILE}/.vimrc ${DIR_CONFIG}/nvim/init.vim
echo 'Linked .vimrc from dotfiles'

ln -sfn ${DIR_DOTFILE}/config/nvim/coc-settings.json ${DIR_CONFIG}/nvim/coc-settings.json
echo 'Linked coc-settings.json from dotfiles'

ln -sfn ${DIR_DOTFILE}/.tmux.conf ${DIR_HOME}/.tmux.conf
echo 'Linked .tmux.conf from dotfiles'
