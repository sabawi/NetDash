#!/bin/bash
# NetDash - Stop Script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$SCRIPT_DIR/.netdash.pid"

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "Stopping NetDash (PID $PID)..."
        kill "$PID"
        sleep 1
        kill -9 "$PID" 2>/dev/null || true
        echo "Stopped."
    else
        echo "NetDash not running (stale PID file)."
    fi
    rm -f "$PID_FILE"
else
    echo "No PID file found. Trying port 8123..."
    if command -v fuser &>/dev/null; then
        fuser -k 8123/tcp 2>/dev/null && echo "Killed." || echo "Nothing on port 8123."
    elif command -v lsof &>/dev/null; then
        lsof -ti:8123 | xargs kill -9 2>/dev/null && echo "Killed." || echo "Nothing on port 8123."
    fi
fi
