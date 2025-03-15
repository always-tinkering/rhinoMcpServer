#!/bin/bash

echo "===== RhinoMCP System Diagnostics ====="
echo "This script will help diagnose issues with the RhinoMCP system"
echo 

# Directory where scripts and files are located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Check if Rhino is running
echo "1. Checking if Rhino is running..."
RHINO_PROCESS=$(ps aux | grep -i "Rhinoceros" | grep -v grep)
if [ -z "$RHINO_PROCESS" ]; then
    echo "❌ ERROR: Rhinoceros is NOT running!"
    echo "   Please start Rhino before running this test."
    RHINO_RUNNING=false
else
    echo "✅ Rhinoceros is running"
    echo "   $RHINO_PROCESS"
    RHINO_RUNNING=true
fi
echo

# Check if the RhinoMcpPlugin.rhp exists
echo "2. Checking if RhinoMcpPlugin.rhp is properly installed..."
PLUGIN_PATH="$HOME/Library/Application Support/McNeel/Rhinoceros/8.0/Plug-ins/RhinoMcpPlugin.rhp"
if [ -f "$PLUGIN_PATH" ]; then
    echo "✅ RhinoMcpPlugin.rhp is installed at the correct location"
    echo "   $PLUGIN_PATH"
    PLUGIN_INSTALLED=true
else
    echo "❌ ERROR: RhinoMcpPlugin.rhp is NOT installed!"
    echo "   Expected location: $PLUGIN_PATH"
    echo "   Please make sure to copy the plugin to the correct location."
    PLUGIN_INSTALLED=false
fi
echo

# Check if the RhinoMcpServer.dll exists
echo "3. Checking if RhinoMcpServer.dll exists..."
SERVER_PATH="$DIR/publish/RhinoMcpServer.dll"
if [ -f "$SERVER_PATH" ]; then
    echo "✅ RhinoMcpServer.dll exists at the correct location"
    echo "   $SERVER_PATH"
    SERVER_EXISTS=true
else
    echo "❌ ERROR: RhinoMcpServer.dll is NOT found!"
    echo "   Expected location: $SERVER_PATH"
    echo "   Please build the server with 'dotnet publish -c Release -o publish'"
    SERVER_EXISTS=false
fi
echo

# Check .NET version compatibility
echo "4. Checking .NET version compatibility..."
DOTNET_VERSION=$(dotnet --version)
echo "   Current .NET SDK version: $DOTNET_VERSION"

# Check the target framework of RhinoMcpServer.dll
SERVER_TARGET_FRAMEWORK=$(grep -o '<TargetFramework>.*</TargetFramework>' "$DIR/RhinoMcpServer.csproj" | sed 's/<TargetFramework>\(.*\)<\/TargetFramework>/\1/')
echo "   Server target framework: $SERVER_TARGET_FRAMEWORK"

# Check installed runtimes
DOTNET_RUNTIMES=$(dotnet --list-runtimes | grep 'Microsoft.NETCore.App')
echo "   Installed .NET runtimes:"
echo "$DOTNET_RUNTIMES"

# Check compatibility
if [[ "$DOTNET_RUNTIMES" == *"$SERVER_TARGET_FRAMEWORK"* ]]; then
    echo "✅ .NET versions are compatible"
    DOTNET_COMPATIBLE=true
else
    echo "❌ WARNING: .NET runtime version mismatch!"
    echo "   The server is targeting $SERVER_TARGET_FRAMEWORK but this version doesn't appear to be installed."
    echo "   Consider updating the target framework in RhinoMcpServer.csproj or installing the required .NET runtime."
    DOTNET_COMPATIBLE=false
fi
echo

# Check if the socket is open
echo "5. Testing connection to RhinoMcpPlugin socket server (port 9876)..."
if nc -z localhost 9876 2>/dev/null; then
    echo "✅ Socket is open on port 9876!"
    echo "   The RhinoMcpPlugin socket server is running and accessible."
    SOCKET_OPEN=true
    
    # Try sending a test command
    echo
    echo "6. Sending test command to get scene info..."
    TEST_RESPONSE=$(echo '{"Type":"get_scene_info","Params":{}}' | nc localhost 9876)
    echo "   Response received:"
    echo "   $TEST_RESPONSE"
    if [ -n "$TEST_RESPONSE" ]; then
        echo "✅ Successfully received a response from the RhinoMcpPlugin socket server!"
    else
        echo "❌ WARNING: No response received from the socket server."
        echo "   The socket is open but the server isn't responding properly."
    fi
else
    echo "❌ ERROR: Could not connect to RhinoMcpPlugin socket server on port 9876"
    echo "   The socket server in Rhino is not running or is not accessible."
    SOCKET_OPEN=false
    
    if [ "$RHINO_RUNNING" = true ]; then
        echo
        echo "   Since Rhino is running, the likely causes are:"
        echo "   1. The RhinoMcpPlugin is not loaded"
        echo "   2. The plugin failed to start the socket server"
        echo "   3. There was an error during plugin initialization"
        echo
        echo "   Please check the Rhino console for any error messages related to RhinoMcpPlugin."
    fi
fi
echo

# Check Claude Desktop configuration
echo "7. Checking Claude Desktop configuration..."
CONFIG_FILE="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
if [ -f "$CONFIG_FILE" ]; then
    echo "✅ Claude Desktop configuration file exists"
    echo "   $CONFIG_FILE"
    
    # Check if the configuration is correct
    CONFIG_CONTENT=$(cat "$CONFIG_FILE")
    echo "   Configuration content:"
    echo "   $CONFIG_CONTENT"
    
    if [[ "$CONFIG_CONTENT" == *"$SERVER_PATH"* ]]; then
        echo "✅ Configuration appears to point to the correct server file"
    else
        echo "❌ WARNING: Configuration might not be pointing to the correct server file!"
        echo "   Expected: $SERVER_PATH"
        echo "   Please check if the paths in the configuration match the actual file locations."
    fi
else
    echo "❌ ERROR: Claude Desktop configuration file not found!"
    echo "   Expected location: $CONFIG_FILE"
    echo "   Please create the configuration file with the correct settings."
fi
echo

# Summary and recommendations
echo "===== Summary ====="
echo

if [ "$RHINO_RUNNING" = false ]; then
    echo "❌ CRITICAL: Rhino needs to be running"
    echo "   Start Rhino and try again"
fi

if [ "$PLUGIN_INSTALLED" = false ]; then
    echo "❌ CRITICAL: RhinoMcpPlugin is not installed"
    echo "   Install the plugin to: $PLUGIN_PATH"
fi

if [ "$SERVER_EXISTS" = false ]; then
    echo "❌ CRITICAL: RhinoMcpServer.dll is missing"
    echo "   Build the server with: dotnet publish -c Release -o publish"
fi

if [ "$DOTNET_COMPATIBLE" = false ]; then
    echo "❌ CRITICAL: .NET version incompatibility"
    echo "   Update RhinoMcpServer.csproj to target an installed .NET version"
fi

if [ "$SOCKET_OPEN" = false ] && [ "$RHINO_RUNNING" = true ] && [ "$PLUGIN_INSTALLED" = true ]; then
    echo "❌ CRITICAL: Plugin socket server is not running"
    echo "   1. Check if the plugin is loaded in Rhino (use PlugInManager command)"
    echo "   2. Check the Rhino console for error messages"
    echo "   3. Try reinstalling the plugin and restarting Rhino"
fi

echo
if [ "$RHINO_RUNNING" = true ] && [ "$PLUGIN_INSTALLED" = true ] && [ "$SERVER_EXISTS" = true ] && [ "$SOCKET_OPEN" = true ]; then
    echo "✅ Core components appear to be working correctly!"
    echo "   If you're still having issues with Claude Desktop, try the following:"
    echo "   1. Restart Claude Desktop"
    echo "   2. Check Claude Desktop logs (look for MCP-related messages)"
    echo "   3. Make sure Claude is properly configured to use the MCP tools"
else
    echo "❌ Some components are not working correctly."
    echo "   Fix the issues highlighted above and try again."
fi

echo
echo "To test the full flow:"
echo "1. Ensure Rhino is running and the plugin is loaded"
echo "2. Start Claude Desktop"
echo "3. In Claude, try a simple command like: 'Create a red sphere at the origin with radius 5'"
echo
echo "For advanced debugging, check:"
echo "- Rhino console for plugin messages"
echo "- Claude Desktop logs"
echo "- Socket communication (e.g., using Wireshark or tcpdump)" 