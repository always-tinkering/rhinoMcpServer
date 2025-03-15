#!/bin/bash

# Wrapper script for running the Python standalone MCP server
# This script ensures the server maintains a connection with Claude
# and handles signals properly

# Set execution directory to script location
cd "$(dirname "$0")"

# Create logs directory if it doesn't exist
mkdir -p logs

# Get timestamp for log files
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="logs/wrapper_${TIMESTAMP}.log"

# Output to log file and terminal
exec > >(tee -a "$LOG_FILE") 2>&1

# Log with timestamp
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*"
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
    
    # Start the Python server with clean stdio
    # DO NOT background this process - Claude Desktop needs direct access to it
    log "Executing ./standalone-mcp-server.py with clean stdio"
    PYTHONUNBUFFERED=1 ./standalone-mcp-server.py
    
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

# Main loop - keep server running
log "==== WRAPPER SCRIPT STARTING ===="
log "Working directory: $(pwd)"

# Start the server for the first time
start_server

# Exit with server's status code
exit $? 