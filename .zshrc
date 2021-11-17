# Default template oh-my-zsh:
# https://github.com/robbyrussell/oh-my-zsh/blob/master/templates/zshrc.zsh-template

#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> Start oh-my-zsh
export ZSH="/home/nb/.oh-my-zsh"

ZSH_THEME="sunaku"

ZSH_TMUX_AUTOSTART=true
ZSH_TMUX_AUTOQUIT=false

plugins=(
  # Shell QoL
  sudo
  zsh-autosuggestions
  web-search

  # Git
  git
  gitfast

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
  cargo
  rustup

  # Tools
  tmux
  fd
  fzf
  ripgrep

  # Editor / IDE
  vscode
)

# Check if Linux or MacOS
if [ "$(uname 2> /dev/null)" != "Linux" ]; then
  # Load MacOS specific plugins
  plugins+=(
    osx
    brew
  )
else
  # Load Ubuntu specific plugins
  plugins+=(
    ubuntu
    command-not-found
  )
fi

# Disable Magic Pasting
# Doc: https://stackoverflow.com/questions/25614613/how-to-disable-zsh-substitution-autocomplete-with-url-and-backslashes
DISABLE_MAGIC_FUNCTIONS=true

source $ZSH/oh-my-zsh.sh

# Fix environment for Wayland + zsh + snapd
source /etc/profile.d/apps-bin-path.sh

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

#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> End oh-my-zsh

# Git
export GPG_TTY=$(tty)
export GIT_EDITOR=nvim

# JQ
#
# Use a more visible colour for nulls.  Default is bright black (1;30), which
# can be difficult to read on terminals with dark background colours.
export JQ_COLORS='0;33:0;39:0;39:0;39:0;32:1;39:1;39'

# FZF
[ -f ~/.fzf.zsh ] && source ~/.fzf.zsh


## Use sharkdp/fd for faster finding
export FZF_DEFAULT_COMMAND='fd --type file'
export FZF_DEFAULT_OPTS='--layout=reverse'

## Preview file with sharkdp/bat
export FZF_CTRL_T_COMMAND="${FZF_DEFAULT_COMMAND}"
export FZF_CTRL_T_OPTS="--preview 'bat --style=numbers --color=always {} 2> /dev/null | head -50'"

## Use Tmux for FZF panel
export FZF_TMUX=1
export FZF_TMUX_HEIGHT=50%

# FZF + GIT
[ -f ~/.dotfiles/.fzfrc ] && source ~/.dotfiles/.fzfrc

# ENV variables
export VISUAL=nvim
export EDITOR="${VISUAL}"

# Ubuntu Snap (this is a problem for Wayland, not for X11)
export PATH=$PATH:/snap/bin

# JAVA
export JAVA_HOME="/usr/lib/jvm/java-8-openjdk-amd64"

# Python
export PATH=$PATH:~/.local/bin

# Golang
export GOPATH=$HOME/work/golang
export PATH=$PATH:/usr/local/go/bin:${GOPATH}/bin

# Rust
export PATH=$PATH:~/.cargo/bin

# Git
export PATH=~/bin:$PATH

# rvm
[[ -s "$HOME/.rvm/scripts/rvm" ]] && . "$HOME/.rvm/scripts/rvm"
# Add RVM to PATH for scripting. Make sure this is the last PATH variable change.
export PATH="$PATH:$HOME/.rvm/bin"

# Toolings
alias cat=bat
alias gotop=gotop-cjbassi
alias ls=lsd
# alias ls=exa # exa is not actively mantained
alias bazel=bazelisk

# Containers
alias kb=kubectl
source <(kubectl completion zsh)

# QoL commands
## List out all dir in ${PATH}
alias path="echo ${PATH} | sed 's/:/\n/g'"
