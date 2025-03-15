#!/bin/bash

# Set execution directory
cd "$(dirname "$0")/RhinoMcpServer"

# Create logs directory if it doesn't exist
mkdir -p logs

# Get timestamp for log files
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
STDERR_LOG="logs/debug_stderr_${TIMESTAMP}.log"
STDOUT_LOG="logs/debug_stdout_${TIMESTAMP}.log"
COMBINED_LOG="logs/debug_combined_${TIMESTAMP}.log"

# Echo status
echo "====================================="
echo "Starting RhinoMcpServer in debug mode"
echo "====================================="
echo "Logging stderr to: $STDERR_LOG"
echo "Logging stdout to: $STDOUT_LOG"
echo "Combined log to: $COMBINED_LOG"
echo "Process ID will be saved to logs/server.pid"

# Run the server with debug flag and capture all output to log files
(
  DOTNET_ENVIRONMENT=Development \
  DOTNET_CLI_UI_LANGUAGE=en \
  DOTNET_CONSOLE_ENCODING=utf-8 \
  dotnet publish/RhinoMcpServer.dll --debug 2> >(tee "$STDERR_LOG") > >(tee "$STDOUT_LOG") | tee "$COMBINED_LOG" & 
  echo $! > logs/server.pid
)

echo "Server started in background with PID $(cat logs/server.pid)"
echo "To stop the server: kill $(cat logs/server.pid)"
echo "To view live logs: tail -f $COMBINED_LOG" 