# Agentic Software Forge — sourced from ~/.zshrc by `asf/scripts/kasten.py setup`.
# Belongs to the template; an update replaces it.

# claude and uv install into ~/.local/bin.
case ":$PATH:" in
    *":$HOME/.local/bin:"*) ;;
    *) export PATH="$HOME/.local/bin:$PATH" ;;
esac

# claude-tmux [name] — Claude Code in a tmux session for the current directory; attaches
# when the session is already running. Optional: nothing starts tmux by itself.
claude-tmux() {
    local name=${1:-${PWD:t}}
    tmux new-session -A -s "$name" -c "$PWD" claude
}
