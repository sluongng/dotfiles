# Default template oh-my-zsh:
# https://github.com/robbyrussell/oh-my-zsh/blob/master/templates/zshrc.zsh-template

#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> Start oh-my-zsh
export ZSH="/home/nb/.oh-my-zsh"

ZSH_THEME="sunaku"

ZSH_TMUX_AUTOSTART=true

plugins=(
  # Shell QoL
  sudo
  zsh-autosuggestions
  web-search

  # Git
  git
  gitfast
  github

  # Containers
  docker
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

# Zsh autosuggestions and histdb
source $HOME/.oh-my-zsh/custom/plugins/zsh-histdb/sqlite-history.zsh
autoload -Uz add-zsh-hook
add-zsh-hook precmd histdb-update-outcome

_zsh_autosuggest_strategy_histdb_top() {
    local query="select commands.argv from
history left join commands on history.command_id = commands.rowid
left join places on history.place_id = places.rowid
where commands.argv LIKE '$(sql_escape $1)%'
group by commands.argv
order by places.dir != '$(sql_escape $PWD)', count(*) desc limit 1"
    suggestion=$(_histdb_query "$query")
}
ZSH_AUTOSUGGEST_STRATEGY=histdb_top

# Ignore duplicate in history when run find (or FZF)
setopt HIST_FIND_NO_DUPS

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
export FZF_TMUX_HEIGHT=50%


#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> START: FZF + GIT

## Enable a powerful set of shortcuts <Ctrl+g><Ctrl+$> to quickly browse git-related resources
## Source: https://gist.github.com/junegunn/8b572b8d4b5eddd8b85e5f4d40f17236

# Check if current folder is inside a git repo
is_in_git_repo() {
  git rev-parse HEAD > /dev/null 2>&1
}

# FZF styling
fzf-down() {
  fzf --height 50% "$@" --border
}

# File
fzf_gf() {
  is_in_git_repo || return
  git -c color.status=always status --short |
  fzf-down -m --ansi --nth 2..,.. \
    --preview '(git diff --color=always -- {-1} | sed 1,4d; cat {-1}) | head -500' |
  cut -c4- | sed 's/.* -> //'
}

# Branch
fzf_gb() {
  is_in_git_repo || return
  git branch -a --color=always | grep -v '/HEAD\s' | sort |
  fzf-down --ansi --multi --tac --preview-window right:70% \
    --preview 'git log --oneline --graph --date=short --color=always --pretty="format:%C(auto)%cd %h%d %s" $(sed s/^..// <<< {} | cut -d" " -f1) | head -'$LINES |
  sed 's/^..//' | cut -d' ' -f1 |
  sed 's#^remotes/##'
}

# Tag
fzf_gt() {
  is_in_git_repo || return
  git tag --sort -version:refname |
  fzf-down --multi --preview-window right:70% \
    --preview 'git show --color=always {} | head -'$LINES
}

# Log / History
fzf_gh() {
  is_in_git_repo || return
  git log --date=short --format="%C(green)%C(bold)%cd %C(auto)%h%d %s (%an)" --graph --color=always |
  fzf-down --ansi --no-sort --reverse --multi --bind 'ctrl-s:toggle-sort' \
    --header 'Press CTRL-S to toggle sort' \
    --preview 'grep -o "[a-f0-9]\{7,\}" <<< {} | xargs git show --color=always | head -'$LINES |
  grep -o "[a-f0-9]\{7,\}"
}

# Remote
fzf_gr() {
  is_in_git_repo || return
  git remote -v | awk '{print $1 "\t" $2}' | uniq |
  fzf-down --tac \
    --preview 'git log --oneline --graph --date=short --pretty="format:%C(auto)%cd %h%d %s" {1} | head -200' |
  cut -d$'\t' -f1
}

# remove new lines 
join-lines() {
  local item
  while read item; do
    echo -n "${(q)item}"
  done
}

# Shortcut binding helper
bind-git-helper() {
  local c
  for c in $@; do
    eval "fzf-g$c-widget() { local result=\$(fzf_g$c | join-lines); zle reset-prompt; LBUFFER+=\$result }"
    eval "zle -N fzf-g$c-widget"
    eval "bindkey '^g^$c' fzf-g$c-widget"
  done
}

# Execute binding and remove helper
bind-git-helper f b t r h
unset -f bind-git-helper

#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> END: FZF + GIT

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

# Toolings
alias cat=bat
# alias ls=exa # exa is not actively mantained
alias ls=lsd
alias gotop=gotop-cjbassi


# Containers
alias kb=kubectl
source <(kubectl completion zsh)

## Podmand need 2 aliaes
## - docker for backward compatibility with scripts
## - pm for ease of use with CLI
alias docker=podman
alias pm=podman

# QoL commands
## List out all dir in ${PATH}
alias path="echo ${PATH} | sed 's/:/\n/g'"
