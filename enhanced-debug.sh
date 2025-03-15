#!/bin/bash

# Enhanced debugging script with comprehensive environment capture
# This script runs the RhinoMcpServer with detailed logging and environment information

# Set execution directory
cd "$(dirname "$0")"

# Create logs directory if it doesn't exist
mkdir -p logs

# Get timestamp for log files
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_DIR="logs/debug_${TIMESTAMP}"
mkdir -p "$LOG_DIR"

# Log files
STDERR_LOG="${LOG_DIR}/stderr.log"
STDOUT_LOG="${LOG_DIR}/stdout.log"
ENV_LOG="${LOG_DIR}/environment.log"
DOTNET_INFO="${LOG_DIR}/dotnet_info.log"
PROCESS_LOG="${LOG_DIR}/process.log"

# Echo status
echo "==============================================="
echo "ENHANCED DEBUGGING FOR RHINOMCPSERVER"
echo "==============================================="
echo "Log directory: $LOG_DIR"

# Capture environment information
echo "Capturing environment information..."

# System info
echo "=== SYSTEM INFO ===" > "$ENV_LOG"
uname -a >> "$ENV_LOG"
echo "" >> "$ENV_LOG"

# .NET info
echo "=== .NET INFO ===" >> "$ENV_LOG"
dotnet --info > "$DOTNET_INFO"
echo "See $DOTNET_INFO for details" >> "$ENV_LOG"
echo "" >> "$ENV_LOG"

# Directory structure
echo "=== DIRECTORY STRUCTURE ===" >> "$ENV_LOG"
find "$(pwd)" -type f -not -path "*/\.*" -not -path "*/logs/*" -not -path "*/bin/*" -not -path "*/obj/*" | sort >> "$ENV_LOG"
echo "" >> "$ENV_LOG"

# Claude configuration
echo "=== CLAUDE CONFIG ===" >> "$ENV_LOG"
if [ -f "$HOME/Library/Application Support/Claude/claude_desktop_config.json" ]; then
    cat "$HOME/Library/Application Support/Claude/claude_desktop_config.json" >> "$ENV_LOG"
else
    echo "Claude config not found" >> "$ENV_LOG"
fi
echo "" >> "$ENV_LOG"

# Run server with complete environment
echo "Starting server with enhanced logging..."
echo "" >> "$ENV_LOG"
echo "=== PROCESS START: $(date) ===" >> "$ENV_LOG"

# Run the server with debug flag and save PID
(
  DOTNET_CLI_UI_LANGUAGE=en \
  DOTNET_ENVIRONMENT=Development \
  DOTNET_CONSOLE_ENCODING=utf-8 \
  DOTNET_ROOT=/usr/local/share/dotnet \
  stdbuf -oL -eL dotnet RhinoMcpServer/publish/RhinoMcpServer.dll --debug 2> >(tee "$STDERR_LOG") > >(tee "$STDOUT_LOG") &
  PID=$!
  
  # Save PID to file for later reference
  echo $PID > "${LOG_DIR}/server.pid"
  
  # Monitor the process and log its status
  echo "PID: $PID" >> "$PROCESS_LOG"
  echo "Start time: $(date)" >> "$PROCESS_LOG"
  
  # Wait for the process and capture exit code
  wait $PID
  EXIT_CODE=$?
  
  echo "Exit code: $EXIT_CODE" >> "$PROCESS_LOG"
  echo "End time: $(date)" >> "$PROCESS_LOG"
)

echo ""
echo "Debugging session completed"
echo "Logs are available in: $LOG_DIR"
echo "To view stderr: cat $STDERR_LOG"
echo "To view stdout: cat $STDOUT_LOG"
echo "To view environment info: cat $ENV_LOG"
echo "===============================================" 