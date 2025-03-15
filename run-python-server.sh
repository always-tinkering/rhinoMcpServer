#!/usr/bin/env bash
# Wrapper script for Rhino MCP Server

# Exit on any error
set -e

# Current directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Create logs directory if it doesn't exist
mkdir -p logs

# Timestamp for log files
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Define the log file
LOG_FILE="logs/server_wrapper_${TIMESTAMP}.log"

# Ensure the Python script is executable
chmod +x ./standalone-mcp-server.py

# Logging function - Log to both terminal and file
log() {
    local msg="[$(date +'%Y-%m-%d %H:%M:%S')] $1"
    echo "$msg" | tee -a "$LOG_FILE" >&2  # Log to stderr, keep stdout clean
}

# Cleanup function
cleanup() {
    log "Cleaning up and shutting down server..."
    
    # Check if we have a PID file
    PID_FILE="logs/standalone_server.pid"
    if [ -f "$PID_FILE" ]; then
        SERVER_PID=$(cat "$PID_FILE")
        log "Server PID found: $SERVER_PID"
        
        if ps -p "$SERVER_PID" > /dev/null; then
            log "Server process is still running, sending termination signal..."
            kill -TERM "$SERVER_PID" || true
            
            # Wait up to 5 seconds for graceful shutdown
            for i in {1..10}; do
                if ! ps -p "$SERVER_PID" > /dev/null; then
                    log "Server exited gracefully"
                    break
                fi
                sleep 0.5
            done
            
            # Force kill if still running
            if ps -p "$SERVER_PID" > /dev/null; then
                log "Server did not exit gracefully, force killing..."
                kill -9 "$SERVER_PID" || true
            fi
        else
            log "Server process was not running"
        fi
        
        rm -f "$PID_FILE"
    fi
    
    log "Cleanup complete"
}

# Set up trap for script exit
trap cleanup EXIT INT TERM

# Start logging
log "==== WRAPPER SCRIPT STARTING ===="
log "Working directory: $SCRIPT_DIR"
log "Python version: $(python3 --version)"

# Check if server script exists and is executable
if [ ! -x "./standalone-mcp-server.py" ]; then
    log "Error: standalone-mcp-server.py not found or not executable"
    exit 1
fi

log "Server script found: $(ls -l ./standalone-mcp-server.py)"

# Clear any existing I/O buffers
python3 -c "import sys; sys.stdout.flush(); sys.stderr.flush()"

# Set environment variables for proper Python I/O handling
export PYTHONUNBUFFERED=1
export PYTHONIOENCODING=utf-8

# Start the server
log "Starting Python server..."
exec python3 ./standalone-mcp-server.py 2>> "$LOG_FILE"

# Note: The script will never reach here due to the exec command above,
# which replaces the current process with the Python server. 