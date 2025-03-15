#!/bin/bash

# Watchdog script that keeps the RhinoMcpServer running
# and properly separates stdout (JSON) from stderr (logs)

# Set execution directory to the script location
cd "$(dirname "$0")"

# Create logs directory if it doesn't exist
mkdir -p logs

# Get timestamp function
get_timestamp() {
  date "+%Y-%m-%d %H:%M:%S"
}

# Function to start the server
start_server() {
  local TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
  local LOG_FILE="logs/server_log_${TIMESTAMP}.log"
  
  echo "[$(get_timestamp)] Starting RhinoMcpServer..." | tee -a "$LOG_FILE"
  echo "[$(get_timestamp)] Process logging to: $LOG_FILE" | tee -a "$LOG_FILE"
  
  # Set critical environment variables for .NET version compatibility
  # These ensure the server can run on .NET 9.x even though it targets .NET 8.0
  export DOTNET_ROLL_FORWARD=LatestMajor
  export DOTNET_ROLL_FORWARD_ON_NO_CANDIDATE_FX=2
  export DOTNET_ROLL_FORWARD_TO_PRERELEASE=1
  
  # Log environment settings
  echo "[$(get_timestamp)] Environment: DOTNET_ROLL_FORWARD=${DOTNET_ROLL_FORWARD}" | tee -a "$LOG_FILE"
  echo "[$(get_timestamp)] Environment: DOTNET_ROLL_FORWARD_ON_NO_CANDIDATE_FX=${DOTNET_ROLL_FORWARD_ON_NO_CANDIDATE_FX}" | tee -a "$LOG_FILE"
  echo "[$(get_timestamp)] Environment: DOTNET_ROLL_FORWARD_TO_PRERELEASE=${DOTNET_ROLL_FORWARD_TO_PRERELEASE}" | tee -a "$LOG_FILE"
  
  # Note: We use nohup to ensure the process continues running if the parent shell exits
  nohup dotnet RhinoMcpServer/publish/RhinoMcpServer.dll >> "$LOG_FILE" 2>&1 &
  
  # Save the PID
  SERVER_PID=$!
  echo $SERVER_PID > logs/server.pid
  
  echo "[$(get_timestamp)] Server started with PID: $SERVER_PID" | tee -a "$LOG_FILE"
  echo "[$(get_timestamp)] Note: The server will remain running during normal client disconnections. This is expected behavior." | tee -a "$LOG_FILE"
  echo "[$(get_timestamp)] The server now creates its own logs in the RhinoMcpServer/publish/logs directory" | tee -a "$LOG_FILE"
}

# Cleanup function to handle graceful shutdown
cleanup() {
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
      start_server
    fi
  else
    echo "[$(get_timestamp)] PID file not found, restarting server..."
    start_server
  fi
  
  # Wait before checking again
  sleep 2
done 