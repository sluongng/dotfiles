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

#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> End oh-my-zsh

# Git
export GPG_TTY=$(tty)
export GIT_EDITOR=nvim

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
## Enable FZF in a tmux floating window
## Note that -p only supported when you use tmux 3.2 or above
## If tmux 3.2 is not yet out, `brew install --HEAD tmux` to
## install it from latest source.
export FZF_TMUX_OPTS="-p 70%"
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

# Add RVM to PATH for scripting. Make sure this is the last PATH variable change.
export PATH="$PATH:$HOME/.rvm/bin"

# rvm
[[ -s "$HOME/.rvm/scripts/rvm" ]] && . "$HOME/.rvm/scripts/rvm"
