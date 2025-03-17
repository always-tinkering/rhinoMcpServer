#!/bin/bash
# Direct launcher for daemon server and socket proxy
# This script launches both components separately

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Function to log messages
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Function to clean up on exit
cleanup() {
    log "Cleaning up..."
    
    pkill -f "daemon_mcp_server.py|socket_proxy.py"
    
    # Remove PID files
    rm -f "$ROOT_DIR/logs/daemon_server.pid" "$ROOT_DIR/logs/socket_proxy.pid"
}

# Set up trap for cleanup
trap cleanup EXIT INT TERM

# Make sure scripts are executable
chmod +x "$ROOT_DIR/src/daemon_mcp_server.py" "$ROOT_DIR/src/socket_proxy.py"

# Check if the scripts exist
if [ ! -x "$ROOT_DIR/src/daemon_mcp_server.py" ]; then
    log "Error: daemon_mcp_server.py not found or not executable"
    exit 1
fi

if [ ! -x "$ROOT_DIR/src/socket_proxy.py" ]; then
    log "Error: socket_proxy.py not found or not executable"
    exit 1
fi

# Make sure no old processes are running
cleanup

# Start the daemon server in the background
log "Starting daemon server..."
"$ROOT_DIR/src/daemon_mcp_server.py" &
daemon_pid=$!
log "Daemon server started with PID: $daemon_pid"

# Wait for daemon to initialize
sleep 2

# Start the socket proxy in the foreground
log "Starting socket proxy..."
"$ROOT_DIR/src/socket_proxy.py"

# Script will clean up on exit 