#!/bin/bash

echo "====================================="
echo "RHINO PLUGIN CONNECTION TESTER"
echo "====================================="
echo "This script will check if the Rhino plugin is running and accessible."
echo "It attempts to connect to the socket server on port 9876."
echo

# Check if Rhino is running
if pgrep -i "Rhinoceros" > /dev/null; then
  echo "✅ Rhino is running"
else
  echo "❌ Rhino is not running. Please start Rhino first."
  exit 1
fi

# Check for the plugin location
PLUGIN_PATH="/Users/$(whoami)/Library/Application Support/McNeel/Rhinoceros/8.0/Plug-ins/RhinoMcpPlugin/RhinoMcpPlugin.rhp"
if [ -f "$PLUGIN_PATH" ]; then
  echo "✅ RhinoMcpPlugin is installed at the correct location"
else
  echo "❌ RhinoMcpPlugin is not installed at: $PLUGIN_PATH"
  exit 1
fi

# Try to connect to the socket server
echo "Testing connection to socket server on port 9876..."
if nc -z -w 2 localhost 9876; then
  echo "✅ Successfully connected to the socket server on port 9876"
  echo "The RhinoMcpPlugin appears to be running correctly!"
else
  echo "❌ Failed to connect to the socket server on port 9876"
  echo
  echo "TROUBLESHOOTING:"
  echo "1. In Rhino, run the command '_PlugInManager' and check if RhinoMcpPlugin is loaded"
  echo "2. If it's not loaded, find it in the list and click 'Load'"
  echo "3. Check the Rhino command window for any error messages"
  echo "4. Restart Rhino and try again"
fi

echo
echo "If the plugin is loaded but the socket server isn't working,"
echo "try restarting Rhino and Claude Desktop." 