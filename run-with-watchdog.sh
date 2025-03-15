#!/bin/bash

# Watchdog script that keeps the RhinoMcpServer running
# and properly separates stdout (JSON) from stderr (logs)
# with JSON validation to ensure only valid JSON is sent to Claude

# Set execution directory to the script location
cd "$(dirname "$0")"

# Create logs directory if it doesn't exist
mkdir -p logs

# Get timestamp function
get_timestamp() {
  date "+%Y-%m-%d %H:%M:%S"
}

# Function to validate JSON
is_valid_json() {
  # Try to parse JSON with jq (minimal)
  if command -v jq &> /dev/null; then
    echo "$1" | jq -e . >/dev/null 2>&1
    return $?
  fi
  
  # Fallback to Python if jq is not available
  if command -v python3 &> /dev/null; then
    echo "$1" | python3 -c "import sys, json; json.load(sys.stdin)" >/dev/null 2>&1
    return $?
  fi
  
  # Fallback to Python2 if Python3 is not available
  if command -v python &> /dev/null; then
    echo "$1" | python -c "import sys, json; json.load(sys.stdin)" >/dev/null 2>&1
    return $?
  fi
  
  # If no validation tools are available, assume it's valid (not ideal but better than nothing)
  return 0
}

# Function to start the server
start_server() {
  local TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
  local LOG_FILE="logs/server_log_${TIMESTAMP}.log"
  local FIFO_FILE="logs/server_fifo_${TIMESTAMP}"
  
  echo "[$(get_timestamp)] Starting RhinoMcpServer..." | tee -a "$LOG_FILE"
  echo "[$(get_timestamp)] Process logging to: $LOG_FILE" | tee -a "$LOG_FILE"
  
  # Set critical environment variables for .NET version compatibility
  # These ensure the server can run on .NET 9.x even though it targets .NET 8.0
  export DOTNET_ROLL_FORWARD=LatestMajor
  export DOTNET_ROLL_FORWARD_ON_NO_CANDIDATE_FX=2
  export DOTNET_ROLL_FORWARD_TO_PRERELEASE=1
  export DOTNET_ENVIRONMENT=Production
  
  # Log environment settings
  echo "[$(get_timestamp)] Environment: DOTNET_ROLL_FORWARD=${DOTNET_ROLL_FORWARD}" | tee -a "$LOG_FILE"
  echo "[$(get_timestamp)] Environment: DOTNET_ROLL_FORWARD_ON_NO_CANDIDATE_FX=${DOTNET_ROLL_FORWARD_ON_NO_CANDIDATE_FX}" | tee -a "$LOG_FILE"
  echo "[$(get_timestamp)] Environment: DOTNET_ROLL_FORWARD_TO_PRERELEASE=${DOTNET_ROLL_FORWARD_TO_PRERELEASE}" | tee -a "$LOG_FILE"
  
  # Create a named pipe for controlled communication
  mkfifo "$FIFO_FILE"
  
  # Set up a proxy script to validate and filter JSON
  cat > "logs/json_filter.py" << 'EOF'
#!/usr/bin/env python3
import sys
import json
import os

def main():
    log_file = os.environ.get('JSON_LOG_FILE', '/dev/null')
    with open(log_file, 'a') as log:
        line_count = 0
        for line in sys.stdin:
            line_count += 1
            line = line.strip()
            if not line:
                continue
                
            try:
                # Try to parse as JSON to validate
                parsed = json.loads(line)
                # If successful, write to stdout for Claude to consume
                print(line)
                sys.stdout.flush()
                log.write(f"VALID JSON [{line_count}]: {line[:100]}...\n")
                log.flush()
            except json.JSONDecodeError as e:
                # If invalid JSON, log it but don't pass to stdout
                log.write(f"INVALID JSON [{line_count}]: {str(e)} in: {line[:100]}...\n")
                log.flush()

if __name__ == "__main__":
    main()
EOF
  
  chmod +x "logs/json_filter.py"
  
  # Start the JSON filter process first, reading from the FIFO
  export JSON_LOG_FILE="$LOG_FILE"
  cat "$FIFO_FILE" | "logs/json_filter.py" &
  FILTER_PID=$!
  echo $FILTER_PID > logs/filter.pid
  
  # Now start the server, with stdout going to the FIFO and stderr to the log file
  # Note: We use nohup to ensure the process continues running if the parent shell exits
  nohup dotnet RhinoMcpServer/publish/RhinoMcpServer.dll > "$FIFO_FILE" 2>> "$LOG_FILE" &
  
  # Save the server PID
  SERVER_PID=$!
  echo $SERVER_PID > logs/server.pid
  
  echo "[$(get_timestamp)] Server started with PID: $SERVER_PID" | tee -a "$LOG_FILE"
  echo "[$(get_timestamp)] Filter process started with PID: $FILTER_PID" | tee -a "$LOG_FILE"
  echo "[$(get_timestamp)] Note: The server will remain running during normal client disconnections. This is expected behavior." | tee -a "$LOG_FILE"
  echo "[$(get_timestamp)] The server now creates its own logs in the RhinoMcpServer/publish/logs directory" | tee -a "$LOG_FILE"
  
  # Save fifo path for cleanup
  echo "$FIFO_FILE" > logs/fifo.path
}

# Cleanup function to handle graceful shutdown
cleanup() {
  echo "[$(get_timestamp)] Starting cleanup..."
  
  # Kill the filter process if running
  if [ -f logs/filter.pid ]; then
    FILTER_PID=$(cat logs/filter.pid)
    if ps -p $FILTER_PID > /dev/null; then
      echo "[$(get_timestamp)] Shutting down JSON filter with PID: $FILTER_PID"
      kill $FILTER_PID 2>/dev/null || kill -9 $FILTER_PID 2>/dev/null
    fi
    rm logs/filter.pid
  fi
  
  # Kill the server process if running
  if [ -f logs/server.pid ]; then
    PID=$(cat logs/server.pid)
    if ps -p $PID > /dev/null; then
      echo "[$(get_timestamp)] Shutting down server with PID: $PID"
      kill $PID
      # Wait for process to terminate
      for i in {1..10}; do
        if ! ps -p $PID > /dev/null; then
          break
        fi
        sleep 0.5
      done
      # Force kill if still running
      if ps -p $PID > /dev/null; then
        echo "[$(get_timestamp)] Server did not exit gracefully, force killing..."
        kill -9 $PID
      fi
    fi
    rm logs/server.pid
  fi
  
  # Remove the FIFO
  if [ -f logs/fifo.path ]; then
    FIFO_FILE=$(cat logs/fifo.path)
    if [ -p "$FIFO_FILE" ]; then
      rm "$FIFO_FILE"
    fi
    rm logs/fifo.path
  fi
  
  echo "[$(get_timestamp)] Cleanup complete"
}

# Set up signal handlers for cleanup on termination
trap cleanup SIGINT SIGTERM EXIT

# Start the server initially
start_server

# Main watchdog loop
echo "[$(get_timestamp)] Watchdog started, monitoring server..."

while true; do
  # Check if the server is running
  if [ -f logs/server.pid ]; then
    PID=$(cat logs/server.pid)
    if ! ps -p $PID > /dev/null; then
      echo "[$(get_timestamp)] Server crashed or exited unexpectedly (PID: $PID)"
      echo "[$(get_timestamp)] Restarting server..."
      cleanup
      start_server
    fi
  else
    echo "[$(get_timestamp)] PID file not found, restarting server..."
    cleanup
    start_server
  fi
  
  # Also check the filter process
  if [ -f logs/filter.pid ]; then
    FILTER_PID=$(cat logs/filter.pid)
    if ! ps -p $FILTER_PID > /dev/null; then
      echo "[$(get_timestamp)] JSON filter crashed (PID: $FILTER_PID)"
      echo "[$(get_timestamp)] Restarting everything..."
      cleanup
      start_server
    fi
  fi
  
  # Wait before checking again
  sleep 2
done 