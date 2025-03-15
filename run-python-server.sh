#!/bin/bash

# Wrapper script to run the Python MCP server with the correct environment
# and ensure it stays running

# Set the execution directory to the script's location
cd "$(dirname "$0")"

# Create logs directory if it doesn't exist
mkdir -p logs

# Timestamp for this run
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="logs/wrapper_${TIMESTAMP}.log"

# Log function
log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Clean up function
cleanup() {
  log "Cleanup: Shutting down any running servers"
  
  # Check for PID file from Python server
  if [ -f "logs/standalone_server.pid" ]; then
    SERVER_PID=$(cat "logs/standalone_server.pid")
    if ps -p "$SERVER_PID" > /dev/null; then
      log "Stopping Python server (PID: $SERVER_PID)"
      kill -2 "$SERVER_PID" 2>/dev/null || kill -9 "$SERVER_PID" 2>/dev/null
    fi
    rm -f "logs/standalone_server.pid"
  fi
  
  log "Cleanup complete"
}

# Set up trap for script exit
trap cleanup EXIT INT TERM

# Start the Python server
log "Starting Python MCP server"

# Set environment variables to help Python
export PYTHONUNBUFFERED=1
export PYTHONDONTWRITEBYTECODE=1

# Start the server - will read from stdin and write to stdout
# We intentionally don't use nohup or background it - Claude Desktop needs direct access
./standalone-mcp-server.py

# Server exit status
EXIT_STATUS=$?
log "Python server exited with status: $EXIT_STATUS"

# Don't exit immediately - give time for Claude to reconnect if needed
sleep 1

exit $EXIT_STATUS 