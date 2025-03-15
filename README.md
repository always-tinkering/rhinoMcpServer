# RhinoMcpServer

A Model Context Protocol (MCP) server implementation for Rhino 3D, enabling seamless integration between Claude AI and Rhino.

## Overview

This project allows Claude to control Rhino 3D through Claude Desktop by implementing the Model Context Protocol. It consists of two main components:

1. **RhinoMcpPlugin**: A Rhino plugin (.NET 7.0) that handles commands from Claude within the Rhino environment
2. **RhinoMcpServer**: A standalone MCP server (.NET 8.0) that bridges Claude Desktop with the Rhino plugin

## Quick Start

1. Start Rhino
2. Run `./check-rhino-plugin.sh` to verify the plugin connection
3. Launch Claude Desktop
4. Start working with Rhino tools in Claude

## Features

- Create and manipulate 3D geometry (spheres, boxes, cylinders)
- Manage scene objects and layers
- Bidirectional communication between Claude and Rhino
- Real-time updates and feedback

## Detailed Architecture

### RhinoMcpPlugin (Rhino Plugin)

- Targets .NET 7.0 for compatibility with Rhino 8
- Implements a socket server on port 9876
- Listens for commands from the MCP server
- Translates commands into Rhino API calls
- Returns results back to the MCP server

### RhinoMcpServer (MCP Server)

- Targets .NET 8.0 for modern features and performance
- Implements the Model Context Protocol
- Communicates with Claude Desktop through stdin/stdout
- Forwards tool calls to the RhinoMcpPlugin via socket connection
- Handles asynchronous communication and error states

## Development Setup

### Prerequisites

- Rhino 8 for Mac
- .NET 8.0 SDK
- Claude Desktop

### Building the Solution

```bash
# Build the plugin
cd RhinoMcpPlugin
dotnet build -c Release

# Build the server
cd ../RhinoMcpServer
dotnet publish -c Release -o publish
```

### Installing the Plugin

```bash
mkdir -p ~/Library/Application\ Support/McNeel/Rhinoceros/8.0/Plug-ins/RhinoMcpPlugin/
cp RhinoMcpPlugin/bin/Release/net7.0/RhinoMcpPlugin.* ~/Library/Application\ Support/McNeel/Rhinoceros/8.0/Plug-ins/RhinoMcpPlugin/
```

### Configure Claude Desktop

Create or update `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "rhino": {
      "command": "dotnet",
      "args": [
        "/Users/[username]/path/to/RhinoMcpServer/publish/RhinoMcpServer.dll"
      ]
    }
  }
}
```

## Troubleshooting

- Use `./debug-server.sh` to run the server with detailed logging
- Use `./check-rhino-plugin.sh` to verify the Rhino plugin is installed and running
- Check for log files in the `RhinoMcpServer/logs` directory

## Version History

- **0.1.0**: Initial implementation with basic geometry creation, server stability improvements, and debugging tools 