#!/bin/bash
# Wrapper script for Rhino MCP Server

# Exit on any error
set -e

# Get timestamp for log files
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="logs/server_wrapper_${TIMESTAMP}.log"

# Ensure logs directory exists
mkdir -p logs

# Function to log messages to both console and file
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Function to cleanup server process
cleanup() {
    log "Cleanup function called"
    if [ -f logs/standalone_server.pid ]; then
        SERVER_PID=$(cat logs/standalone_server.pid)
        if ps -p $SERVER_PID > /dev/null; then
            log "Sending SIGTERM to server process $SERVER_PID"
            kill -TERM $SERVER_PID 2>/dev/null || true
            # Wait for graceful shutdown
            for i in {1..10}; do
                if ! ps -p $SERVER_PID > /dev/null; then
                    break
                fi
                sleep 0.5
            done
            # Force kill if still running
            if ps -p $SERVER_PID > /dev/null; then
                log "Server didn't exit gracefully, force killing..."
                kill -9 $SERVER_PID 2>/dev/null || true
            fi
        fi
        rm -f logs/standalone_server.pid
    fi
}

# Set up trap for script exit
trap cleanup EXIT INT TERM

# Log script start
log "==== WRAPPER SCRIPT STARTING ===="
log "Working directory: $(pwd)"
log "Python version: $(python3 --version)"

# Verify server script exists and is executable
if [ ! -x ./standalone-mcp-server.py ]; then
    chmod +x ./standalone-mcp-server.py
fi

log "Server script found: $(ls -l ./standalone-mcp-server.py)"

# Set environment variables for Python I/O handling
export PYTHONUNBUFFERED=1
export PYTHONIOENCODING=utf-8

# Clear any existing I/O buffers
if [ -t 0 ]; then stty -F /dev/tty -icanon -echo; fi

log "Starting Python server..."

# Start the server and keep it running
while true; do
    # Start the server in the background
    ./standalone-mcp-server.py 2>> "$LOG_FILE" &
    SERVER_PID=$!
    echo $SERVER_PID > logs/standalone_server.pid
    
    # Wait for server process
    wait $SERVER_PID || true
    
    # Check if we should restart
    if [ -f logs/standalone_server.pid ]; then
        log "Server exited, but PID file exists. Restarting..."
        sleep 1
    else
        log "Server shutdown requested, exiting wrapper"
        break
    fi
done

log "==== WRAPPER SCRIPT EXITING ====" 