#!/bin/bash

echo "===== Starting RhinoMCP Environment ====="
echo "This script will help start and verify all components of the RhinoMCP system"
echo 

# Directory where scripts and files are located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Check if Rhino is running
echo "1. Checking if Rhino is running..."
RHINO_PROCESS=$(ps aux | grep -i "Rhinoceros" | grep -v grep)
if [ -z "$RHINO_PROCESS" ]; then
    echo "❌ ERROR: Rhinoceros is NOT running!"
    echo "   Please start Rhino before continuing."
    echo
    read -p "Start Rhino now? (y/n): " START_RHINO
    if [[ "$START_RHINO" =~ ^[Yy]$ ]]; then
        echo "Starting Rhino..."
        open -a "Rhino 8"
        echo "Waiting for Rhino to start..."
        sleep 10
        echo "Rhino should be starting now."
    else
        echo "Please start Rhino manually."
        exit 1
    fi
else
    echo "✅ Rhinoceros is already running"
fi
echo

# Check if the RhinoMcpPlugin.rhp exists
echo "2. Checking if RhinoMcpPlugin.rhp is properly installed..."
PLUGIN_PATH="$HOME/Library/Application Support/McNeel/Rhinoceros/8.0/Plug-ins/RhinoMcpPlugin.rhp"
if [ -f "$PLUGIN_PATH" ]; then
    echo "✅ RhinoMcpPlugin.rhp is installed at the correct location"
else
    echo "❌ ERROR: RhinoMcpPlugin.rhp is NOT installed!"
    echo "   Expected location: $PLUGIN_PATH"
    
    if [ -f "$DIR/RhinoMcpPlugin/bin/Release/net48/RhinoMcpPlugin.rhp" ]; then
        echo "   Found plugin at: $DIR/RhinoMcpPlugin/bin/Release/net48/RhinoMcpPlugin.rhp"
        echo "   Copying plugin to the correct location..."
        
        mkdir -p "$(dirname "$PLUGIN_PATH")"
        cp "$DIR/RhinoMcpPlugin/bin/Release/net48/RhinoMcpPlugin.rhp" "$PLUGIN_PATH"
        
        if [ $? -eq 0 ]; then
            echo "✅ Plugin successfully copied"
        else
            echo "❌ Failed to copy plugin"
            exit 1
        fi
    else
        echo "   Plugin not found in expected build location."
        echo "   Please build the plugin and manually copy it to: $PLUGIN_PATH"
        exit 1
    fi
fi
echo

# Check if the RhinoMcpServer.dll exists
echo "3. Checking if RhinoMcpServer.dll exists..."
SERVER_PATH="$DIR/RhinoMcpServer/publish/RhinoMcpServer.dll"
if [ -f "$SERVER_PATH" ]; then
    echo "✅ RhinoMcpServer.dll exists at the correct location"
else
    echo "❌ ERROR: RhinoMcpServer.dll is NOT found!"
    echo "   Expected location: $SERVER_PATH"
    echo "   Building server..."
    
    cd "$DIR/RhinoMcpServer"
    dotnet publish -c Release -o publish
    
    if [ $? -eq 0 ]; then
        echo "✅ Server successfully built"
    else
        echo "❌ Failed to build server"
        exit 1
    fi
fi
echo

# Update Claude Desktop configuration
echo "4. Updating Claude Desktop configuration..."
CONFIG_FILE="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
mkdir -p "$(dirname "$CONFIG_FILE")"

echo '{
  "mcpServers": {
    "rhino": {
      "command": "dotnet",
      "args": [
        "'"$SERVER_PATH"'",
        "--verbose"
      ]
    }
  }
}' > "$CONFIG_FILE"

echo "✅ Claude Desktop configuration updated"
echo "   Location: $CONFIG_FILE"
echo

# Important instructions for Rhino
echo "5. IMPORTANT: Verify RhinoMcpPlugin in Rhino..."
echo "   1. In Rhino, type the command: PlugInManager"
echo "   2. Look for 'RhinoMcpPlugin' in the list"
echo "   3. If it's not loaded, click 'Load' to enable it"
echo "   4. Open the Rhino Console (Window > Rhino Console)"
echo "   5. Look for messages about the socket server starting"
echo
echo "   The plugin should show a message like:"
echo "   'RhinoMcpPlugin: Starting socket server on port 9876'"
echo
read -p "Press Enter when you've verified the plugin is loaded in Rhino..."
echo

# Test connectivity
echo "6. Testing connection to RhinoMcpPlugin socket server..."
"$DIR/RhinoMcpServer/test-connection.sh"
echo

# Start Claude Desktop
echo "7. Starting Claude Desktop..."
echo "   Please ensure Claude Desktop is installed on your system."
echo "   The configuration has been updated to use the RhinoMcpServer."
echo
read -p "Start Claude Desktop now? (y/n): " START_CLAUDE
if [[ "$START_CLAUDE" =~ ^[Yy]$ ]]; then
    echo "Starting Claude Desktop..."
    open -a "Claude"
    echo "Claude Desktop should be starting now."
    echo "When using Claude, try commands like:"
    echo "   'Create a red sphere with radius 5 at the origin in Rhino'"
else
    echo "Please start Claude Desktop manually when ready."
fi
echo

echo "===== Environment Setup Complete ====="
echo "If you encounter issues:"
echo "1. Run the diagnostic script: $DIR/RhinoMcpServer/debug-system.sh"
echo "2. Check the Rhino console for error messages"
echo "3. Restart all components in this order: Rhino, then Claude Desktop"
echo
echo "Happy creating with RhinoMCP!" 