#!/bin/bash

echo "==== RhinoMcpServer Process Checker ===="
echo 

# Check if the server is running
PS_OUTPUT=$(ps aux | grep -i "RhinoMcpServer.dll" | grep -v grep)

if [ -z "$PS_OUTPUT" ]; then
    echo "RhinoMcpServer is NOT currently running."
    echo
    echo "Would you like to start it now? (y/n)"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        echo "Starting RhinoMcpServer..."
        DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
        # Start in background and capture PID
        dotnet "$DIR/publish/RhinoMcpServer.dll" &
        SERVER_PID=$!
        echo "Server started with PID: $SERVER_PID"
        sleep 2  # Give it a moment to initialize
    else
        echo "Not starting the server. Exiting."
        exit 0
    fi
else
    echo "RhinoMcpServer is currently running!"
    echo "$PS_OUTPUT"
    SERVER_PID=$(echo "$PS_OUTPUT" | awk '{print $2}')
fi

# Now show details about the process
echo
echo "==== Server Process Details ===="
echo

# Show process info
ps -p "$SERVER_PID" -o pid,ppid,user,%cpu,%mem,vsz,rss,tt,stat,start,time,command

# Show network connections
echo
echo "==== Network Connections ===="
echo
lsof -i -n -P | grep dotnet

# Show process tree
echo
echo "==== Process Tree ===="
echo
pstree -p "$SERVER_PID" 2>/dev/null || echo "pstree command not available"

echo
echo "==== How to Monitor the Server ===="
echo "1. Use Activity Monitor and search for 'dotnet'"
echo "2. Run 'lsof -i -n -P | grep dotnet' to see network connections"
echo "3. Run 'ps aux | grep -i \"RhinoMcpServer.dll\" | grep -v grep' to check if it's running"
echo
echo "To stop the server, run: kill $SERVER_PID" 