#!/bin/bash
# Run combined MCP server for Rhino

# Ensure the script directory is always available
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# Create log directories if they don't exist
LOG_ROOT="$SCRIPT_DIR/logs"
mkdir -p "$LOG_ROOT/server"
mkdir -p "$LOG_ROOT/plugin"
mkdir -p "$LOG_ROOT/claude"
mkdir -p "$LOG_ROOT/diagnostics"

# Check if the MCP server is already running
if [ -f "$LOG_ROOT/combined_server.pid" ]; then
    PID=$(cat "$LOG_ROOT/combined_server.pid")
    if ps -p $PID > /dev/null; then
        echo "MCP server is already running with PID $PID"
        echo "To stop it, use: kill $PID"
        echo "To view logs in real-time: ./log_manager.py monitor"
        exit 1
    else
        echo "Stale PID file found. Removing..."
        rm "$LOG_ROOT/combined_server.pid"
    fi
fi

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed. Please install Python 3 and try again."
    exit 1
fi

# Display information about logging
echo "Starting RhinoMcpServer with unified logging system"
echo "Log files will be created in: $LOG_ROOT"
echo "To monitor logs in real-time: ./log_manager.py monitor"
echo "To view error reports: ./log_manager.py errors"
echo "For more information: cat LOGGING.md"
echo ""

# Run the combined MCP server
chmod +x combined_mcp_server.py
python3 combined_mcp_server.py 