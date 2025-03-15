#!/bin/bash

# Enhanced Debug Script for RhinoMcpServer
# This script runs the server with detailed diagnostic information
# and captures logs for debugging purposes.

# Set -e to exit on error, -u to error on undefined variables
set -e
set -u

# Get a timestamp for log filenames
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_DIR="./logs"
DEBUG_LOG="${LOG_DIR}/debug_${TIMESTAMP}.log"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Create a function to echo with timestamp
log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$DEBUG_LOG"
}

# Log system information
log "===== ENHANCED DEBUG MODE STARTED ====="
log "System: $(uname -a)"
log "Current directory: $(pwd)"
log "User: $(whoami)"
log "Path: $PATH"

# Log .NET information
log "=== .NET RUNTIME INFO ==="
if command -v dotnet &> /dev/null; then
  log "dotnet version: $(dotnet --version)"
  log "dotnet info:"
  dotnet --info | tee -a "$DEBUG_LOG"
else
  log "ERROR: dotnet not found in PATH"
  exit 1
fi

# Check for the RhinoMcpServer.dll
SERVER_DLL="./RhinoMcpServer/publish/RhinoMcpServer.dll"
if [ ! -f "$SERVER_DLL" ]; then
  log "ERROR: Server DLL not found at $SERVER_DLL"
  log "Current directory contents:"
  ls -la | tee -a "$DEBUG_LOG"
  
  log "Attempting to find the DLL:"
  find . -name "RhinoMcpServer.dll" | tee -a "$DEBUG_LOG"
  exit 1
fi

# Log project file and dependencies
log "=== PROJECT INFO ==="
log "Project file contents:"
cat ./RhinoMcpServer/RhinoMcpServer.csproj | tee -a "$DEBUG_LOG"

# Log environment variables
log "=== ENVIRONMENT VARIABLES ==="
env | grep -i "DOTNET\|NET\|PATH" | sort | tee -a "$DEBUG_LOG"

# Set diagnostic environment variables
export DOTNET_CLI_CAPTURE_TIMING=1
export DOTNET_ROLL_FORWARD=LatestMajor
export DOTNET_ROLL_FORWARD_ON_NO_CANDIDATE_FX=2
export DOTNET_ROLL_FORWARD_TO_PRERELEASE=1
export DOTNET_MULTILEVEL_LOOKUP=1
export DOTNET_CLI_UI_LANGUAGE=en-US
export DOTNET_NOLOGO=0
export DOTNET_CLI_TELEMETRY_OPTOUT=1
export DOTNET_LOGGING__CONSOLE__DISABLECOLORS=true
export DOTNET_LOGGING__CONSOLE__FORMAT=json

# Output the environment variables after setting
log "Set diagnostics environment variables:"
env | grep -i "DOTNET\|NET" | sort | tee -a "$DEBUG_LOG"

# Run the server with full verbosity
log "Starting server with full diagnostics..."
log "Command: dotnet $SERVER_DLL --diagnostics --debug"

# Start the server and save both stdout and stderr to the log file
# The 2>&1 redirects stderr to stdout, and the tee -a appends it to the log file
dotnet $SERVER_DLL --diagnostics --debug 2>&1 | tee -a "$DEBUG_LOG"

# This part will only execute if the server exits (normally it should run indefinitely)
EXIT_CODE=$?
log "Server exited with code: $EXIT_CODE"

# Post-mortem analysis
log "=== POST-MORTEM ANALYSIS ==="
log "Last 30 lines of log:"
tail -n 30 "$DEBUG_LOG" | tee -a "${LOG_DIR}/postmortem_${TIMESTAMP}.log"

log "Memory usage at time of exit:"
ps aux | grep -i dotnet | tee -a "${LOG_DIR}/postmortem_${TIMESTAMP}.log"

log "Disk space:"
df -h | tee -a "${LOG_DIR}/postmortem_${TIMESTAMP}.log"

log "Network connections:"
netstat -anp 2>/dev/null | grep -i dotnet | tee -a "${LOG_DIR}/postmortem_${TIMESTAMP}.log" || true

log "===== DEBUG SESSION ENDED ====="
log "Full debug log available at: $DEBUG_LOG"
log "Post-mortem analysis: ${LOG_DIR}/postmortem_${TIMESTAMP}.log"

# Exit with the same code as the server
exit $EXIT_CODE 