# Default template oh-my-zsh:
# https://github.com/robbyrussell/oh-my-zsh/blob/master/templates/zshrc.zsh-template

## Start oh-my-zsh
export ZSH="/home/nb/.oh-my-zsh"

ZSH_THEME="sunaku"

plugins=(
  docker
  docker-compose
  git
	github
  sudo
  zsh-autosuggestions
  mvn
  node
  kubectl
  spring
  golang
)

source $ZSH/oh-my-zsh.sh
## End oh-my-zsh

# Git
export GPG_TTY=$(tty)

# FZF
[ -f ~/.fzf.zsh ] && source ~/.fzf.zsh

# JAVA
export JAVA_HOME="/usr/lib/jvm/java-8-openjdk-amd64"

# Python
export PATH=$PATH:~/.local/bin

# Golang
export PATH=$PATH:/usr/local/go/bin
export GOPATH=$HOME/work/golang

# Aliases
alias cat=bat
alias ls=lsd
alias fd=fdfind

## Podmand need 2 aliaes
## - docker for backward compatibility with scripts
## - pm for ease of use with CLI
alias docker=podman
alias pm=podman
