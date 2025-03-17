#!/bin/bash
# Wrapper script for the combined MCP server

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Function to log messages to stderr
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >&2
}

# Function to clean up on exit
cleanup() {
    log "Cleaning up..."
    
    # Check if the server PID file exists
    PID_FILE="$ROOT_DIR/logs/combined_server.pid"
    if [ -f "$PID_FILE" ]; then
        SERVER_PID=$(cat "$PID_FILE")
        log "Found server PID: $SERVER_PID"
        
        # Check if the process is running
        if kill -0 $SERVER_PID 2>/dev/null; then
            log "Stopping server process..."
            kill -TERM $SERVER_PID
            
            # Wait for process to exit
            for i in {1..5}; do
                if ! kill -0 $SERVER_PID 2>/dev/null; then
                    log "Server process stopped"
                    break
                fi
                log "Waiting for server to exit (attempt $i)..."
                sleep 1
            done
            
            # Force kill if still running
            if kill -0 $SERVER_PID 2>/dev/null; then
                log "Server still running, force killing..."
                kill -9 $SERVER_PID
            fi
        else
            log "Server process not running"
        fi
        
        # Remove PID file
        rm -f "$PID_FILE"
    fi
}

# Set up trap for cleanup
trap cleanup EXIT INT TERM

# Make the server script executable
chmod +x "$ROOT_DIR/src/combined_mcp_server.py"

# Check if the server script exists
if [ ! -x "$ROOT_DIR/src/combined_mcp_server.py" ]; then
    log "Error: combined_mcp_server.py not found or not executable"
    exit 1
fi

# Make sure no old processes are running
cleanup

# Set up Python's stdin/stdout
export PYTHONUNBUFFERED=1
export PYTHONIOENCODING=utf-8

# Clear any existing input
while read -t 0; do read -r; done

# Start the server in the foreground
log "Starting combined MCP server..."
exec "$ROOT_DIR/src/combined_mcp_server.py" 