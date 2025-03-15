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

# Ensure the Python script is executable
chmod +x ./standalone-mcp-server.py

# Define the log file
LOG_FILE="logs/server_wrapper_${TIMESTAMP}.log"

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
            
            # Wait a moment for the process to terminate gracefully
            sleep 2
            
            # Force kill if still running
            if ps -p "$SERVER_PID" > /dev/null; then
                log "Server still running after TERM signal, sending KILL signal..."
                kill -9 "$SERVER_PID" || true
            fi
        else
            log "Server process is not running"
        fi
        
        # Remove the PID file
        rm -f "$PID_FILE"
    fi
    
    log "Cleanup complete"
}

# Trap script exit
trap cleanup EXIT

# Log script start
log "==== WRAPPER SCRIPT STARTING ===="
log "Working directory: $(pwd)"

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1)
log "Python version: $PYTHON_VERSION"

# Check if the Python server script exists
if [ -f "./standalone-mcp-server.py" ]; then
    log "Server script found: $(ls -la ./standalone-mcp-server.py)"
else
    log "ERROR: Server script not found!"
    exit 1
fi

# Clear any I/O buffers before starting the server
# This is crucial for clean stdin/stdout communication
log "Clearing I/O buffers before starting server"

# Set environment variables for Python
export PYTHONUNBUFFERED=1
export PYTHONIOENCODING=utf-8

# CRITICAL: For the MCP protocol, we need to exec the Python process directly
# rather than running it as a subprocess. This allows it to inherit the stdin/stdout
# pipes directly from Claude without any intermediate process.
log "Replacing wrapper with Python server process to ensure clean I/O connections"

# IMPORTANT: We need to redirect stderr to our log file, but leave stdout
# completely clean for the JSON communication
exec python3 ./standalone-mcp-server.py 2>> "$LOG_FILE"

# Note: The script will never reach here due to the exec command above,
# which replaces the current process with the Python server. 