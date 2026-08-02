# Default template oh-my-zsh:
# https://github.com/robbyrussell/oh-my-zsh/blob/master/templates/zshrc.zsh-template

#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> Start oh-my-zsh
export ZSH="$HOME/.oh-my-zsh"

typeset -gU path
DOTFILES_OS="$(uname -s 2>/dev/null)"

_path_prepend() {
  [[ -d "$1" ]] && path=("$1" "${path[@]}")
}

_path_append() {
  [[ -d "$1" ]] && path+=("$1")
}

ZSH_THEME="sunaku"

# Only auto-start tmux for local top-level terminal shells.
if [[ -t 1 && -z "$TMUX" && -z "$SSH_CONNECTION" && -z "$SSH_TTY" && -z "$SSH_CLIENT" ]]; then
  ZSH_TMUX_AUTOSTART=true
  ZSH_TMUX_AUTOQUIT=true
else
  ZSH_TMUX_AUTOSTART=false
  ZSH_TMUX_AUTOQUIT=false
fi

SHOW_AWS_PROMPT=false

# M1 Mac
# Brew switched to /opt/homebrew
if [[ "$(uname -m)" == 'arm64' && "$DOTFILES_OS" == 'Darwin' ]]; then
  _path_prepend /opt/homebrew/sbin
  _path_prepend /opt/homebrew/bin
  _path_prepend /usr/local/bin
  export LIB="/opt/homebrew/lib${LIB:+:${LIB}}"
  export INCLUDE="/opt/homebrew/include${INCLUDE:+:${INCLUDE}}"

  # Need to compile git
  export C_INCLUDE_PATH=$INCLUDE
  export LIBRARY_PATH=$LIB
fi

plugins=(
  # Shell QoL
  sudo
  web-search

  # Git
  git
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

  # Cloud
  aws

  # Editor / IDE
  vscode
)

if [[ -t 1 ]]; then
  plugins+=(
    zsh-autosuggestions
    tmux
    fzf
  )
fi

if command -v brew >/dev/null 2>&1; then
  FPATH="$(brew --prefix)/share/zsh/site-functions:${FPATH}"
fi

# Keep distro-specific oh-my-zsh plugins off the other operating system.
if [[ "$DOTFILES_OS" == "Darwin" ]]; then
  plugins+=(
    macos
  )
  command -v brew >/dev/null 2>&1 && plugins+=(brew)
elif [[ "$DOTFILES_OS" == "Linux" ]]; then
  if command -v pacman >/dev/null 2>&1; then
    plugins+=(archlinux)
  elif command -v apt >/dev/null 2>&1; then
    plugins+=(ubuntu command-not-found)
  fi

  # Fix environment for Wayland + zsh + snapd
  if [ -r /etc/profile.d/apps-bin-path.sh ]; then
    source /etc/profile.d/apps-bin-path.sh
  fi
fi

# Disable Magic Pasting
# Doc: https://stackoverflow.com/questions/25614613/how-to-disable-zsh-substitution-autocomplete-with-url-and-backslashes
DISABLE_MAGIC_FUNCTIONS=true

if [[ -r "$ZSH/oh-my-zsh.sh" ]]; then
  source "$ZSH/oh-my-zsh.sh"
else
  print -u2 "dotfiles: oh-my-zsh is not installed at $ZSH; continuing without it"
fi

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
if [[ -t 0 ]]; then
  export GPG_TTY=$(tty)
fi
if command -v nvim >/dev/null 2>&1; then
  export GIT_EDITOR=nvim
else
  export GIT_EDITOR=vi
fi

# JQ
#
# Use a more visible colour for nulls.  Default is bright black (1;30), which
# can be difficult to read on terminals with dark background colours.
export JQ_COLORS='0;33:0;39:0;39:0;39:0;32:1;39:1;39'

# Ripgrep sane defaults
if [ -f "$HOME/.ripgreprc" ]; then
  export RIPGREP_CONFIG_PATH=$HOME/.ripgreprc
fi

# FZF
[[ -t 1 && -f ~/.fzf.zsh ]] && source ~/.fzf.zsh

# Sourcegraph local MCP token for Codex.
if [[ -z "${SOURCEGRAPH_MCP_TOKEN:-}" && -r "$HOME/.local/share/sourcegraph/admin-credentials" ]]; then
  SOURCEGRAPH_MCP_TOKEN="$(awk -F= '$1=="mcp_token"{print substr($0,index($0,$2)); exit}' "$HOME/.local/share/sourcegraph/admin-credentials")"
  export SOURCEGRAPH_MCP_TOKEN
fi


## Use sharkdp/fd for faster finding when it is installed.
if command -v fd >/dev/null 2>&1; then
  export FZF_DEFAULT_COMMAND='fd --type file'
  export FZF_ALT_C_COMMAND='fd --type directory'
else
  export FZF_DEFAULT_COMMAND='find . -type f'
  export FZF_ALT_C_COMMAND='find . -type d'
fi
export FZF_DEFAULT_OPTS='--layout=reverse'
# Pin fzf to the terminal's One Dark palette instead of relying on
# fzf/tmux popup defaults, which can drift across package upgrades.
FZF_DEFAULT_OPTS+=' --color=dark,bg:#282c34,bg+:#3e4452,fg:#aab2bf,fg+:#abb2bf,hl:#61afef,hl+:#61afef,info:#e5c07b,prompt:#98c379,pointer:#e06c75,marker:#e06c75,spinner:#61afef,header:#5c6370,border:#5c6370'

## Preview file with sharkdp/bat
export FZF_CTRL_T_COMMAND="${FZF_DEFAULT_COMMAND}"
if command -v bat >/dev/null 2>&1; then
  export FZF_CTRL_T_OPTS="--preview 'bat --style=numbers --color=always {} 2> /dev/null | head -100'"
fi

## Navigate to dir
export FZF_ALT_C_OPTS="--preview 'lsd -l {}'"

## Use Tmux for FZF panel
export FZF_TMUX=1
export FZF_TMUX_OPTS='-p 70%'
export FZF_TMUX_HEIGHT=50%

# FZF + GIT
[[ -t 1 && -f ~/.dotfiles/.fzfrc ]] && source ~/.dotfiles/.fzfrc

# ENV variables
if command -v nvim >/dev/null 2>&1; then
  export VISUAL=nvim
else
  export VISUAL=vi
fi
export EDITOR="${VISUAL}"

# Ubuntu Snap (this is a problem for Wayland, not for X11)
[[ "$DOTFILES_OS" == "Linux" ]] && _path_append /snap/bin

# JAVA
case "$DOTFILES_OS" in
  Darwin)
    if [[ -d /opt/homebrew/opt/openjdk/libexec/openjdk.jdk/Contents/Home ]]; then
      export JAVA_HOME="/opt/homebrew/opt/openjdk/libexec/openjdk.jdk/Contents/Home"
      _path_prepend /opt/homebrew/opt/openjdk/bin
    fi
    ;;
  Linux)
    if [[ -d /usr/lib/jvm/java-25-openjdk ]]; then
      export JAVA_HOME="/usr/lib/jvm/java-25-openjdk"
      _path_prepend "$JAVA_HOME/bin"
    fi
    ;;
esac

# Golang
export GOPATH=$HOME/work/golang
_path_append /usr/local/go/bin
_path_append "${GOPATH}/bin"

# Rust
_path_append "$HOME/.cargo/bin"

# Git
_path_prepend "$HOME/bin"
if [[ "$DOTFILES_OS" == 'Darwin' && -n "${commands[brew]:-}" ]]; then
  export XML_CATALOG_FILES="$(brew --prefix)/etc/xml/catalog"
  export MANPATH="$HOME/share/man${MANPATH:+:${MANPATH}}"
fi

# rvm
[[ -s "$HOME/.rvm/scripts/rvm" ]] && . "$HOME/.rvm/scripts/rvm"
# Add RVM helpers for scripting when RVM is installed.
_path_append "$HOME/.rvm/bin"

# File that keeps secrets
if [[ -f ~/secret.sh ]]; then
  source ~/secret.sh
fi

# Toolings
command -v bat >/dev/null 2>&1 && alias cat=bat
# alias ls=lsd
command -v eza >/dev/null 2>&1 && alias ls=eza
# alias bazel=bazelisk

# Use the stock Codex profile automatically for the stock-analysis checkout.
_codex_uses_stock_profile() {
  local target="$PWD"
  local stock_root="$HOME/work/misc/stock"
  local expect_cd_arg=0
  local arg

  stock_root="${stock_root:A}"
  for arg in "$@"; do
    if (( expect_cd_arg )); then
      target="$arg"
      expect_cd_arg=0
      continue
    fi

    case "$arg" in
      --profile|-p|--profile=*|-p?*)
        return 1
        ;;
      --cd|-C)
        expect_cd_arg=1
        ;;
      --cd=*)
        target="${arg#--cd=}"
        ;;
      -C?*)
        target="${arg#-C}"
        ;;
      --)
        break
        ;;
    esac
  done

  target="${target:A}"
  [[ "$target" == "$stock_root" || "$target" == "$stock_root/"* ]]
}

_codex_profile_supports_command() {
  local expect_value=0
  local arg
  local -a positional

  for arg in "$@"; do
    if (( expect_value )); then
      expect_value=0
      continue
    fi

    case "$arg" in
      --help|-h|--version|-V)
        return 1
        ;;
      -c|--config|-i|--image|-m|--model|-p|--profile|-s|--sandbox|-C|--cd|--add-dir|-a|--ask-for-approval|--remote|--remote-auth-token-env|--local-provider)
        expect_value=1
        ;;
      --config=*|--image=*|--model=*|--profile=*|--sandbox=*|--cd=*|--add-dir=*|--ask-for-approval=*|--remote=*|--remote-auth-token-env=*|--local-provider=*)
        ;;
      -[cipmsaC]?*)
        ;;
      --)
        break
        ;;
      --*)
        ;;
      -*)
        ;;
      *)
        positional+=("$arg")
        ;;
    esac
  done

  case "${positional[1]}" in
    ""|exec|e|review|resume|archive|delete|unarchive|fork|mcp|sandbox)
      return 0
      ;;
    debug)
      [[ "${positional[2]}" == "prompt-input" ]]
      return
      ;;
    login|logout|plugin|mcp-server|app-server|remote-control|completion|update|doctor|apply|a|cloud|exec-server|features|help)
      return 1
      ;;
    *)
      # Unknown first positional arguments are treated as interactive prompts.
      return 0
      ;;
  esac
}

codex() {
  local codex_home="${CODEX_HOME:-$HOME/.codex}"

  if [[ "${CODEX_STOCK_PROFILE_AUTO:-1}" != 0 ]] &&
     [[ "${codex_home:A}" == "${HOME}/.codex" ]] &&
     _codex_profile_supports_command "$@" &&
     _codex_uses_stock_profile "$@"; then
    command codex --profile stock "$@"
    return
  fi

  command codex "$@"
}

# Codex personal account. Uses the same codex binary with isolated state.
alias codexp='CODEX_HOME="$HOME/.codexp" codex'

# Containers
if command -v kubectl >/dev/null 2>&1; then
  alias kb=kubectl
fi

# QoL commands
## List out all dir in ${PATH}
alias path='print -r -- "$PATH" | tr ":" "\n" | sort | uniq -c | sort -n'

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

# Enable core dumps to debug Bazel JVM issue
# https://github.com/bazelbuild/bazel/issues/23497
ulimit -c unlimited 2>/dev/null || true
ulimit -n 10240 2>/dev/null || true
if [[ "$DOTFILES_OS" == 'Darwin' ]]; then
  _path_append /opt/homebrew/opt/binutils/bin
  _path_prepend /opt/homebrew/opt/curl/bin
  _path_prepend /opt/homebrew/opt/bison/bin
fi

# gsutil currently supports Python 3.9-3.13; prefer uv-managed 3.13 when available.
_gsutil_python_cache="${XDG_CACHE_HOME:-$HOME/.cache}/gsutil-python-3.13"
if [[ -r "${_gsutil_python_cache}" ]]; then
  _gsutil_python="$(<"${_gsutil_python_cache}")"
fi
if [[ ! -x "${_gsutil_python:-}" ]] && command -v uv >/dev/null 2>&1; then
  _gsutil_python="$(uv python find 3.13 2>/dev/null)"
  if [[ -x "${_gsutil_python}" ]]; then
    mkdir -p "${_gsutil_python_cache:h}"
    print -r -- "${_gsutil_python}" >| "${_gsutil_python_cache}"
  fi
fi
if [[ -x "${_gsutil_python:-}" ]]; then
  export CLOUDSDK_PYTHON="${_gsutil_python}"
fi
unset _gsutil_python _gsutil_python_cache


# Added by Antigravity CLI installer
_path_prepend "$HOME/.local/bin"

unset -f _path_prepend _path_append
unset DOTFILES_OS
