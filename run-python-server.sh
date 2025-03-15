#!/bin/bash

# Wrapper script for running the Python standalone MCP server
# This script ensures the server maintains a connection with Claude
# and handles signals properly

# Set script to exit on any error
set -e

# Set execution directory to script location
cd "$(dirname "$0")"

# Create logs directory if it doesn't exist
mkdir -p logs

# Get timestamp for log files
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="logs/wrapper_${TIMESTAMP}.log"

# Make sure Python script is executable
chmod +x ./standalone-mcp-server.py

# Log with timestamp
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE" >&2
}

# Function to clean up when the script exits
cleanup() {
    log "Wrapper script is shutting down..."
    
    # Check if we have a PID file
    if [ -f "logs/standalone_server.pid" ]; then
        SERVER_PID=$(cat logs/standalone_server.pid)
        if ps -p $SERVER_PID > /dev/null; then
            log "Stopping Python server (PID: $SERVER_PID)"
            # Send SIGTERM first for graceful shutdown
            kill -15 $SERVER_PID 2>/dev/null
            
            # Wait up to 3 seconds for graceful exit
            for i in {1..30}; do
                if ! ps -p $SERVER_PID > /dev/null; then
                    log "Server exited gracefully"
                    break
                fi
                sleep 0.1
            done
            
            # If still running, force kill
            if ps -p $SERVER_PID > /dev/null; then
                log "Server did not exit gracefully, sending SIGKILL"
                kill -9 $SERVER_PID 2>/dev/null
            fi
        else
            log "Server process not found (PID: $SERVER_PID)"
        fi
        
        # Remove PID file
        rm -f logs/standalone_server.pid
    fi
    
    log "Cleanup complete"
}

# Trap script exit
trap cleanup EXIT INT TERM

# Function to start the server
start_server() {
    log "Starting Python MCP server"
    log "Note: The server will remain running during normal client disconnections. This is expected behavior."
    
    # Ensure we're in the correct directory
    cd "$(dirname "$0")"
    
    # Set environment variables to help Python
    export PYTHONUNBUFFERED=1
    export PYTHONIOENCODING=utf-8
    
    # Clear any existing stdout/stderr buffers
    log "Clearing I/O buffers"
    
    # Start the Python server with clean stdio
    # CRITICAL: We must NOT redirect stdin, as the Python server needs to receive stdin directly from Claude
    # We only redirect stderr to our log file, keeping stdin and stdout connected to Claude
    log "Executing ./standalone-mcp-server.py with direct stdin/stdout connection to Claude"
    
    # CRITICAL FIX: Do not redirect stdin - let it pass straight from Claude to the Python script
    # Only redirect stderr to our log file
    ./standalone-mcp-server.py 2>> "$LOG_FILE"
    
    # This is reached when the Python server exits
    RESULT=$?
    log "Server exited with status $RESULT"
    
    # Check if server exited with special code indicating it should not be restarted
    if [ $RESULT -eq 143 ]; then
        log "Server exited with code 143 (SIGTERM) - normal shutdown"
        return 143
    elif [ $RESULT -eq 130 ]; then
        log "Server exited with code 130 (SIGINT) - normal shutdown"
        return 130
    fi
    
    # For any other exit code, we'll restart after a delay
    if [ $RESULT -ne 0 ]; then
        log "Server exited with error code $RESULT - will restart after delay"
    else
        log "Server exited normally - will restart after delay"
    fi
    
    return $RESULT
}

# Main script execution
log "==== WRAPPER SCRIPT STARTING ===="
log "Working directory: $(pwd)"
log "Python version: $(python3 --version 2>&1)"

# Check that we have the server script
if [ ! -f "./standalone-mcp-server.py" ]; then
    log "ERROR: standalone-mcp-server.py not found in current directory"
    exit 1
fi

log "Server script found: $(ls -la ./standalone-mcp-server.py)"

# Start the server - CRITICAL: We call exec here to replace the current process
# This ensures stdin/stdout are directly connected between Claude and the Python server
log "Replacing wrapper with Python server process to ensure clean I/O connections"
exec ./standalone-mcp-server.py 2>> "$LOG_FILE"

# Note: The code below will never be reached due to the exec command above
# This ensures that there's no shell process in between Claude and the Python server
log "If you see this message, exec failed!"
start_server
exit $? 