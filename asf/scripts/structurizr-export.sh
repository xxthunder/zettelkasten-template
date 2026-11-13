#!/bin/bash

# structurizr-export.sh
# Exports the views of the Structurizr viewer on --port as SVG into --out, with Puppeteer's container image.
# Uses a viewer that already answers on the port; otherwise starts one (structurizr-local.sh) and stops it afterwards.
# Uses podman if available, otherwise docker.
# Exit Codes:
# 0: Views exported
# 1: Prereq failure (no container runtime)
# 2: The viewer did not answer within 120 seconds
# 4: Argument error
# other: exit code of the container runtime

USAGE="Usage: $0 --out=<dir> [--port=<port>]"
# Fully qualified: podman resolves a short name only when its registries.conf lists search registries
IMAGE="ghcr.io/puppeteer/puppeteer"
PORT=8080
OUT=""

for arg in "$@"; do
  case $arg in
    --port=*)
      PORT="${arg#*=}"
      ;;
    --out=*)
      OUT="${arg#*=}"
      ;;
    *)
      echo "Error: Unknown argument: $arg" >&2
      echo "$USAGE" >&2
      exit 4
      ;;
  esac
done

if [ -z "$OUT" ]; then
    echo "Error: --out is required." >&2
    echo "$USAGE" >&2
    exit 4
fi

if ! [[ "$PORT" =~ ^[0-9]+$ ]] || [ "$PORT" -lt 1 ] || [ "$PORT" -gt 65535 ]; then
    echo "Error: --port must be a number between 1 and 65535." >&2
    echo "$USAGE" >&2
    exit 4
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Podman first: where both commands exist, docker is most likely podman's alias
if command -v podman >/dev/null 2>&1; then
    RUNTIME=podman
    # The image's user pptruser (uid 10042, gid 999) needs its own home for Chrome; mapping the
    # calling user onto it keeps the written SVGs editable by the caller
    RUN_AS=(--userns=keep-id:uid=10042,gid=999)
elif command -v docker >/dev/null 2>&1; then
    RUNTIME=docker
    # Run as the calling user, so the SVGs stay editable; that user has no home in the image,
    # so Chrome gets a writable one in /tmp
    RUN_AS=(--user "$(id -u):$(id -g)" -e HOME=/tmp)
else
    echo "Error: neither podman nor docker found. Install one of them." >&2
    exit 1
fi

mkdir -p "$OUT" || exit 4
OUT="$(cd "$OUT" && pwd)"

URL="http://localhost:$PORT"

VIEWER_PID=""
stop_viewer() {
    if [ -n "$VIEWER_PID" ]; then
        kill "$VIEWER_PID" 2>/dev/null
        wait "$VIEWER_PID" 2>/dev/null
    fi
}
trap stop_viewer EXIT

# A viewer that answers already belongs to someone else: neither start nor stop it
if ! curl -sf -o /dev/null -m 2 "$URL"; then
    "$SCRIPT_DIR/structurizr-local.sh" --port="$PORT" &
    VIEWER_PID=$!
    ready=false
    for ((i = 0; i < 120; i++)); do
        if curl -sf -o /dev/null -m 2 "$URL"; then
            ready=true
            break
        fi
        sleep 1
    done
    if [ "$ready" != true ]; then
        echo "Error: the viewer did not answer within 120 seconds." >&2
        exit 2
    fi
fi

"$RUNTIME" run --rm --network host "${RUN_AS[@]}" -e NODE_PATH=/home/pptruser/node_modules \
    -v "$SCRIPT_DIR:/scripts:ro" -v "$OUT:/out" "$IMAGE" \
    node /scripts/structurizr-export.js "$URL/workspace/1/diagrams" /out
exit $?
