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
#
# Goals:
# - Provisioned all configuration files

DIR_DOTFILE=~/.dotfiles
DIR_HOME=${HOME}
DIR_CONFIG=${XDG_CONFIG_HOME:-${DIR_HOME}/.config}

# Clone repo
if [ ! -d "${DIR_HOME}/.dotfiles" ]; then
  git clone https://github.com/sluongng/dotfiles.git ${DIR_DOTFILE}
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

if [ -f "${DIR_HOME}/.ideavimrc" ]; then
  cp ${DIR_HOME}/.ideavimrc ${DIR_HOME}/.ideavimrc.bak
  echo 'Done back up IntelliJ IDEA Vim config'
else
  echo 'No .ideavimrc found'
fi

if [ -f "${DIR_CONFIG}/nvim/init.vim" ]; then
  cp ${DIR_CONFIG}/nvim/.luarc.json ${DIR_CONFIG}/nvim/.luarc.json.bak
  cp ${DIR_CONFIG}/nvim/init.lua ${DIR_CONFIG}/nvim/init.lua.bak
  echo 'Done back up neovim config'
else
  echo 'No init.vim(neovim config) found'
fi

if [ -f "${DIR_CONFIG}/libinput-gestures.conf" ]; then
  cp ${DIR_CONFIG}/config/libinput-gestures.conf ${DIR_CONFIG}/config/libinput-gestures.conf.bak
  echo 'Done back up libinput-gestures config'
else
  echo 'No libinput-gestures config found'
fi

if [ -f "${DIR_CONFIG}/alacritty/alacritty.yml" ]; then
  cp ${DIR_CONFIG}/alacritty/alacritty.yml ${DIR_CONFIG}/alacritty/alacritty.yml.bak
  echo 'Done back up alacritty config'
else
  echo 'No alacritty config found'
fi

if [ -f "${DIR_CONFIG}/kitty/kitty.conf" ]; then
  cp ${DIR_CONFIG}/kitty/kitty.conf ${DIR_CONFIG}/kitty/kitty.conf.bak
  echo 'Done back up kitty config'
else
  echo 'No kitty config found'
fi

if [ -f "${DIR_CONFIG}/bat/config" ]; then
  cp ${DIR_CONFIG}/bat/config ${DIR_CONFIG}/bat/config.bak
  echo 'Done back up bat config'
else
  echo 'No bat config found'
fi

if [ -f "${DIR_HOME}/.tmux.conf" ]; then
  cp ${DIR_HOME}/.tmux.conf ${DIR_HOME}/.tmux.conf.bak
  echo 'Done back up tmux config'
else
  echo 'No .tmux.conf(tmux config) found'
fi

# Provisioning directories
mkdir -p ${DIR_CONFIG}/nvim/
mkdir -p ${DIR_CONFIG}/alacritty/
mkdir -p ${DIR_CONFIG}/kitty/
mkdir -p ${DIR_CONFIG}/bat/
mkdir -p ${DIR_CONFIG}/git/

# Link all the dotfiles
ln -sfn ${DIR_DOTFILE}/.zshrc ${DIR_HOME}/.zshrc
echo 'Linked .zshrc from dotfiles'

# ln -sfn ${DIR_DOTFILE}/.vimrc ${DIR_HOME}/.vimrc
ln -sfn ${DIR_DOTFILE}/nvim/init.lua ${DIR_CONFIG}/nvim/init.lua
ln -sfn ${DIR_DOTFILE}/nvim/.luarc.json ${DIR_CONFIG}/nvim/.luarc.json
echo 'Linked nvim/init.lua from dotfiles'

ln -sfn ${DIR_DOTFILE}/.ideavimrc ${DIR_HOME}/.ideavimrc
echo 'Linked .ideavimrc from dotfiles'

ln -sfn ${DIR_DOTFILE}/.tmux.conf ${DIR_HOME}/.tmux.conf
echo 'Linked .tmux.conf from dotfiles'

ln -sfn ${DIR_DOTFILE}/config/libinput-gestures.conf ${DIR_CONFIG}/libinput-gestures.conf
echo 'Linked libinput-gestures config from dotfiles'

ln -sfn ${DIR_DOTFILE}/config/git/config ${DIR_CONFIG}/git/config
echo 'Linked git config from dotfiles'

ln -sfn ${DIR_DOTFILE}/config/alacritty/alacritty.yml ${DIR_CONFIG}/alacritty/alacritty.yml
echo 'Linked alacritty config from dotfiles'

ln -sfn ${DIR_DOTFILE}/config/kitty/kitty.conf ${DIR_CONFIG}/kitty/kitty.conf
ln -sfn ${DIR_DOTFILE}/config/kitty/one-dark.conf ${DIR_CONFIG}/kitty/one-dark.conf
echo 'Linked kitty config from dotfiles'

ln -sfn ${DIR_DOTFILE}/config/bat/config ${DIR_CONFIG}/bat/config
echo 'Linked bat config from dotfiles'

# Install Homebrew and brew packages
# TODO: Detects MacOS
(
  # TODO: Check and skip if 'brew' exists
  # echo 'Installing Homebrew (requires sudo)'
  # /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

  # TODO: Check if Brewfile exists
  echo 'Installing all MacOS brew packages using Brewfile'
  cd ${DIR_DOTFILE}
  brew bundle install
)

# TODO: Install oh-my-zsh and fzf

# TODO: What about Ubuntu and apt/snap packages?

# TODO: Install and update neovim + coc.nvim + treesitter plugins/extensions
