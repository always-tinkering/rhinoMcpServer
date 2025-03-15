#!/bin/bash

echo "=== RhinoMcpPlugin Connection Test ==="
echo "This script tests if the RhinoMcpPlugin socket server is running in Rhino"
echo 

# Check if Rhino is running
ps_output=$(ps aux | grep -i "Rhinoceros" | grep -v grep)
if [ -z "$ps_output" ]; then
    echo "ERROR: Rhinoceros does not appear to be running!"
    echo "Please start Rhino before running this test."
    exit 1
else
    echo "✓ Rhinoceros is running"
fi

# Test connection to the plugin socket server
echo "Testing connection to RhinoMcpPlugin on port 9876..."
if nc -z localhost 9876 2>/dev/null; then
    echo "✓ Successfully connected to RhinoMcpPlugin socket server on port 9876!"
    
    # Try sending a simple command
    echo "Sending test command to get scene info..."
    
    echo '{
  "Type": "get_scene_info",
  "Params": {}
}' | nc localhost 9876
    
    echo
    echo "If you see a JSON response above, the connection is working properly!"
else
    echo "ERROR: Could not connect to RhinoMcpPlugin socket server on port 9876"
    echo "Please ensure:"
    echo "1. Rhino is running"
    echo "2. The RhinoMcpPlugin is loaded in Rhino"
    echo "3. The socket server in the plugin has started"
    echo
    echo "You can check the Rhino console for plugin loading messages."
fi

echo
echo "=== Claude Desktop Configuration ==="
config_file="/Users/angerman/Library/Application Support/Claude/claude_desktop_config.json"
if [ -f "$config_file" ]; then
    echo "Your Claude Desktop configuration:"
    cat "$config_file"
else
    echo "Could not find Claude Desktop configuration file!"
fi 