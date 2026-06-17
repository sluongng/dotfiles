# Keep login zsh shells aligned with interactive shells for local tools.
typeset -gU path
[[ -d "$HOME/.local/bin" ]] && path=("$HOME/.local/bin" "${path[@]}")
