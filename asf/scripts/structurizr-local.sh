#!/bin/bash

# structurizr-local.sh
# Starts Structurizr local (the structurizr/structurizr image) on the architecture in asf/architecture.
# Runs in the foreground; Ctrl+C stops and removes the container. Uses podman if available, otherwise docker.
# --open opens the view in the browser ($BROWSER, else xdg-open) once the viewer answers.
# A copy of shortcuts' tools/structurizr/structurizr-local.sh, adapted to the Kasten (ZKK-015).
# Exit Codes:
# 0: Viewer stopped
# 1: Prereq failure (no container runtime)
# 4: Argument error
# other: exit code of the container runtime

USAGE="Usage: $0 [--port=<port>] [--open]"
# Fully qualified: podman resolves a short name only when its registries.conf lists search registries
IMAGE="docker.io/structurizr/structurizr"
PORT=8080
OPEN=false
OPEN_TIMEOUT=120

for arg in "$@"; do
  case $arg in
    --port=*)
      PORT="${arg#*=}"
      ;;
    --open)
      OPEN=true
      ;;
    *)
      echo "Error: Unknown argument: $arg" >&2
      echo "$USAGE" >&2
      exit 4
      ;;
  esac
done

if ! [[ "$PORT" =~ ^[0-9]+$ ]] || [ "$PORT" -lt 1 ] || [ "$PORT" -gt 65535 ]; then
    echo "Error: --port must be a number between 1 and 65535." >&2
    echo "$USAGE" >&2
    exit 4
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="$(cd "$SCRIPT_DIR/../architecture" && pwd)"

# Podman first: where both commands exist, docker is most likely podman's alias
if command -v podman >/dev/null 2>&1; then
    RUNTIME=podman
    # The image runs as uid 65532, which rootless podman maps to a subordinate uid that cannot
    # write the mounted directory; keep-id maps the calling user into the container unchanged
    RUN_AS=(--userns=keep-id --user "$(id -u):$(id -g)")
elif command -v docker >/dev/null 2>&1; then
    RUNTIME=docker
    # Run as the calling user, so the files Structurizr writes into the repository stay editable
    RUN_AS=(--user "$(id -u):$(id -g)")
else
    echo "Error: neither podman nor docker found. Install one of them." >&2
    exit 1
fi

URL="http://localhost:$PORT"

# Waits in the background until the viewer answers, then opens it; the exec below replaces this shell
open_when_ready() {
    for ((i = 0; i < OPEN_TIMEOUT; i++)); do
        if curl -sf -o /dev/null -m 2 "$URL"; then
            "${BROWSER:-xdg-open}" "$URL"
            return
        fi
        sleep 1
    done
    echo "Error: the viewer did not answer within $OPEN_TIMEOUT seconds; open $URL yourself." >&2
}
[ "$OPEN" = true ] && open_when_ready &

TTY=()
[ -t 0 ] && TTY=(-it)

echo "Structurizr local on $URL (Ctrl+C to stop), model: $WORKSPACE_DIR"
exec "$RUNTIME" run "${TTY[@]}" --rm "${RUN_AS[@]}" -p "$PORT:8080" -v "$WORKSPACE_DIR:/usr/local/structurizr" "$IMAGE" local
