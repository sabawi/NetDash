#!/bin/bash
# NetDash - Start Script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$SCRIPT_DIR/.netdash.pid"
LOG_FILE="$SCRIPT_DIR/netdash.log"
VENV="$SCRIPT_DIR/venv"

# Stop any existing instance
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo "Stopping existing NetDash (PID $OLD_PID)..."
        kill "$OLD_PID"
        sleep 1
    fi
    rm -f "$PID_FILE"
fi

# Also kill anything on port 8123
fuser -k 8123/tcp 2>/dev/null || true

# Activate virtual environment
if [ -f "$VENV/bin/activate" ]; then
    source "$VENV/bin/activate"
else
    echo "WARNING: venv not found at $VENV — using system Python"
fi

echo "Starting NetDash on http://0.0.0.0:8123 ..."
cd "$SCRIPT_DIR"
nohup python3 netdash.py > "$LOG_FILE" 2>&1 &
PID=$!
echo $PID > "$PID_FILE"
echo "NetDash started (PID $PID)"
echo "Log: $LOG_FILE"
echo "URL: http://localhost:8123"
