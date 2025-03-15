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
DOTNET_VERSIONS="${LOG_DIR}/dotnet_versions.log"
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

# .NET SDK and Runtime versions
echo "=== .NET SDK VERSIONS ===" > "$DOTNET_VERSIONS"
dotnet --list-sdks >> "$DOTNET_VERSIONS"
echo "" >> "$DOTNET_VERSIONS"
echo "=== .NET RUNTIME VERSIONS ===" >> "$DOTNET_VERSIONS"
dotnet --list-runtimes >> "$DOTNET_VERSIONS"
echo "" >> "$DOTNET_VERSIONS"
echo "See $DOTNET_VERSIONS for details" >> "$ENV_LOG"
echo "" >> "$ENV_LOG"

# Check publish directory
echo "=== PUBLISHED SERVER FILES ===" >> "$ENV_LOG"
find "$(pwd)/RhinoMcpServer/publish" -type f | sort >> "$ENV_LOG"
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

# Check for server process already running
echo "=== CHECKING FOR EXISTING SERVER PROCESSES ===" >> "$ENV_LOG"
ps aux | grep "RhinoMcpServer.dll" | grep -v grep >> "$ENV_LOG" || echo "No RhinoMcpServer processes found" >> "$ENV_LOG"
echo "" >> "$ENV_LOG"

# Run server with complete environment
echo "Starting server with enhanced logging..."
echo "" >> "$ENV_LOG"
echo "=== PROCESS START: $(date) ===" >> "$ENV_LOG"

# Set up comprehensive environment variables for .NET
export DOTNET_CLI_UI_LANGUAGE=en
export DOTNET_ENVIRONMENT=Development
export DOTNET_CONSOLE_ENCODING=utf-8
export DOTNET_ROOT=/usr/local/share/dotnet
export DOTNET_ROLL_FORWARD=Major
export DOTNET_ROLL_FORWARD_TO_PRERELEASE=1
export DOTNET_MULTILEVEL_LOOKUP=1
export DOTNET_CLI_TELEMETRY_OPTOUT=1

# Record environment variables being used
echo "=== DOTNET ENVIRONMENT VARIABLES ===" >> "$ENV_LOG"
env | grep DOTNET_ >> "$ENV_LOG"
echo "" >> "$ENV_LOG"

# Run the server with debug flag and save PID
(
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
  
  # Check for crash files
  if [ -d "$HOME/Library/Logs/DiagnosticReports" ]; then
    echo "Checking for crash reports..." >> "$PROCESS_LOG"
    find "$HOME/Library/Logs/DiagnosticReports" -name "dotnet_*" -cmin -10 >> "$PROCESS_LOG"
  fi
)

echo ""
echo "Debugging session completed"
echo "Logs are available in: $LOG_DIR"
echo "To view stderr: cat $STDERR_LOG"
echo "To view stdout: cat $STDOUT_LOG"
echo "To view environment info: cat $ENV_LOG"
echo "===============================================" 