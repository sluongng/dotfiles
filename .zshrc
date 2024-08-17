# Default template oh-my-zsh:
# https://github.com/robbyrussell/oh-my-zsh/blob/master/templates/zshrc.zsh-template

#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> Start oh-my-zsh
export ZSH="$HOME/.oh-my-zsh"

ZSH_THEME="sunaku"

ZSH_TMUX_AUTOSTART=false
ZSH_TMUX_AUTOQUIT=false

SHOW_AWS_PROMPT=false

# M1 Mac
# Brew switched to /opt/homebrew
if [[ `uname -m` == 'arm64' && `uname` == 'Darwin' ]]; then
  export PATH=/usr/local/bin:/opt/homebrew/bin:/opt/homebrew/sbin:$PATH
  export LIB=/opt/homebrew/lib:$LIB
  export INCLUDE=/opt/homebrew/include:$INCLUDE

  # Need to compile git
  export C_INCLUDE_PATH=$INCLUDE
  export LIBRARY_PATH=$LIB
fi

plugins=(
  # Shell QoL
  sudo
  zsh-autosuggestions
  web-search

  # Git
  git
  gitfast
  gh

  # Containers
  docker
  docker-compose
  kubectl
  minikube
  helm

  # Languages
  mvn
  pip
  npm
  golang
  spring
  rust

  # Tools
  tmux
  fzf

  # Cloud
  aws

  # Editor / IDE
  vscode
)

if type brew &>/dev/null
then
  FPATH="$(brew --prefix)/share/zsh/site-functions:${FPATH}"

  autoload -Uz compinit
  compinit
fi

# Check if Linux or MacOS
if [ "$(uname 2> /dev/null)" != "Linux" ]; then
  # Load MacOS specific plugins
  plugins+=(
    macos
    brew
  )
else
  # Load Ubuntu specific plugins
  plugins+=(
    ubuntu
    command-not-found
  )

  # Fix environment for Wayland + zsh + snapd
  source /etc/profile.d/apps-bin-path.sh
fi

# Disable Magic Pasting
# Doc: https://stackoverflow.com/questions/25614613/how-to-disable-zsh-substitution-autocomplete-with-url-and-backslashes
DISABLE_MAGIC_FUNCTIONS=true

source $ZSH/oh-my-zsh.sh

# Enhanced zsh history

# Zsh autosuggestions and histdb
# source $HOME/.oh-my-zsh/custom/plugins/zsh-histdb/sqlite-history.zsh
# autoload -Uz add-zsh-hook
# add-zsh-hook precmd histdb-update-outcome
# 
# _zsh_autosuggest_strategy_histdb_top() {
#     local query="select commands.argv from
# history left join commands on history.command_id = commands.rowid
# left join places on history.place_id = places.rowid
# where commands.argv LIKE '$(sql_escape $1)%'
# group by commands.argv
# order by places.dir != '$(sql_escape $PWD)', count(*) desc limit 1"
#     suggestion=$(_histdb_query "$query")
# }
# ZSH_AUTOSUGGEST_STRATEGY=histdb_top

# Ignore duplicate in history when run find (or FZF)
setopt HIST_FIND_NO_DUPS

# Ignore history that is longer than 100 characters
# ZSH_AUTOSUGGEST_HISTORY_IGNORE='?(#c100,)'

#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> End oh-my-zsh

# Git
export GPG_TTY=$(tty)
export GIT_EDITOR=nvim

# JQ
#
# Use a more visible colour for nulls.  Default is bright black (1;30), which
# can be difficult to read on terminals with dark background colours.
export JQ_COLORS='0;33:0;39:0;39:0;39:0;32:1;39:1;39'

# Ripgrep sane defaults
export RIPGREP_CONFIG_PATH=$HOME/.ripgreprc

# FZF
[ -f ~/.fzf.zsh ] && source ~/.fzf.zsh


## Use sharkdp/fd for faster finding
export FZF_DEFAULT_COMMAND='fd --type file'
export FZF_DEFAULT_OPTS='--layout=reverse'

## Preview file with sharkdp/bat
export FZF_CTRL_T_COMMAND="${FZF_DEFAULT_COMMAND}"
export FZF_CTRL_T_OPTS="--preview 'bat --style=numbers --color=always {} 2> /dev/null | head -50'"

## Navigate to dir
export FZF_ALT_C_COMMAND='fd --type directory'
export FZF_ALT_C_OPTS="--preview 'lsd -l {}'"

## Use Tmux for FZF panel
export FZF_TMUX=1
export FZF_TMUX_OPTS='-p 70%'
export FZF_TMUX_HEIGHT=50%

# FZF + GIT
[ -f ~/.dotfiles/.fzfrc ] && source ~/.dotfiles/.fzfrc

# ENV variables
export VISUAL=nvim
export EDITOR="${VISUAL}"

# Ubuntu Snap (this is a problem for Wayland, not for X11)
export PATH=$PATH:/snap/bin

# JAVA
export JAVA_HOME="/opt/homebrew/opt/openjdk/libexec/openjdk.jdk/Contents/Home"
export PATH="/opt/homebrew/opt/openjdk/bin:$PATH"

# Python
export PATH=$PATH:~/.local/bin

# Golang
export GOPATH=$HOME/work/golang
export PATH=$PATH:/usr/local/go/bin:${GOPATH}/bin

# Rust
export PATH=$PATH:~/.cargo/bin

# Git
export PATH=~/bin:$PATH
if [[ `uname` == 'Darwin' ]]; then
  export XML_CATALOG_FILES="$(brew --prefix)/etc/xml/catalog"
  export MANPATH=$HOME/share/man:$MANPATH
fi

# rvm
[[ -s "$HOME/.rvm/scripts/rvm" ]] && . "$HOME/.rvm/scripts/rvm"
# Add RVM to PATH for scripting. Make sure this is the last PATH variable change.
export PATH="$PATH:$HOME/.rvm/bin"

# File that keeps secrets
if [[ -f ~/secret.sh ]]; then
  source ~/secret.sh
fi

# Toolings
alias icat='kitten icat --align=left'
alias cat=bat
alias gotop=gotop-cjbassi
# alias ls=lsd
alias ls=eza # eza is not actively mantained
# alias bazel=bazelisk

# Containers
alias kb=kubectl
source <(kubectl completion zsh)

# QoL commands
## List out all dir in ${PATH}
alias path="echo ${PATH} | sed 's/:/\n/g'"

# Use bat for man pager
export PAGER='less -FX'
export MANPAGER='nvim +Man!'
export MANROFFOPT='-c'

# Bazel / Gazelle
export GO_REPOSITORY_USE_HOST_CACHE=1
export DOCKER_REPO_CACHE="${HOME}/.bazel/docker_repo_cache"

# Terraform
alias tf=terraform
export KUBE_CONFIG_PATH=~/.kube/config

# tabtab source for packages
# uninstall by removing these lines
[[ -f ~/.config/tabtab/zsh/__tabtab.zsh ]] && . ~/.config/tabtab/zsh/__tabtab.zsh || true

export PATH="$PATH:/opt/homebrew/opt/binutils/bin"
