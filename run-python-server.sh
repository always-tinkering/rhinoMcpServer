#!/bin/bash

# Wrapper script to run the Python MCP server with the correct environment
# and ensure it stays running with proper I/O handling for Claude Desktop

# Set the execution directory to the script's location
cd "$(dirname "$0")"

# Create logs directory if it doesn't exist
mkdir -p logs

# Timestamp for this run
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="logs/wrapper_${TIMESTAMP}.log"

# Log function - always to stderr or log file, never stdout
log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >&2
}

# Clean up function
cleanup() {
  log "Cleanup: Shutting down any running servers"
  
  # Check for PID file from Python server
  if [ -f "logs/standalone_server.pid" ]; then
    SERVER_PID=$(cat "logs/standalone_server.pid")
    if ps -p "$SERVER_PID" > /dev/null; then
      log "Stopping Python server (PID: $SERVER_PID)"
      kill -15 "$SERVER_PID" 2>/dev/null || kill -9 "$SERVER_PID" 2>/dev/null
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
export PYTHONIOENCODING=utf-8

# We need to ensure Claude gets clean input/output without shell interference
# Execute Python directly, redirecting all logs to stderr and log file
# While keeping stdout clean for JSON communication
log "Executing ./standalone-mcp-server.py with clean stdio"

# Run Python with exec to replace this process
# This ensures proper handling of stdin/stdout with no intermediaries
exec ./standalone-mcp-server.py 2>> "$LOG_FILE"

# This code will not be executed due to exec, but including for documentation
EXIT_STATUS=$?
log "Python server exited with status: $EXIT_STATUS"
exit $EXIT_STATUS 