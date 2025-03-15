#!/bin/bash

# Test connection to RhinoMcpPlugin socket server on port 9876
# This script should be run after starting Rhino with the plugin loaded

echo "Testing connection to RhinoMcpPlugin socket server..."
nc -zv localhost 9876

if [ $? -eq 0 ]; then
    echo "Connection successful! The RhinoMcpPlugin socket server is running."
else
    echo "Connection failed. Make sure:"
    echo "1. Rhino is running"
    echo "2. The RhinoMcpPlugin is loaded (use PlugInManager command in Rhino)"
    echo "3. There are no firewall issues blocking the connection"
fi 