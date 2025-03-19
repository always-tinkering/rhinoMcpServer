# Rhino MCP Server

> **⚠️ UNDER CONSTRUCTION ⚠️**  
> This project is currently under active development and is not yet in working order. The Rhino plugin is experiencing issues with creating objects.
> We are actively seeking support from the community to help resolve these issues.
> If you have experience with Rhino API development, C# plugins, or MCP integration, please consider contributing.
> Contact us by opening an issue on GitHub.

A Model Context Protocol (MCP) server implementation for Rhino 3D, allowing Claude to create and manipulate 3D objects.

## Overview

This project implements an MCP server for Rhino 3D that enables AI assistants like Claude to interact with Rhino through the Model Context Protocol. The server allows for the creation and manipulation of 3D objects directly from the AI interface.

## Components

There are several implementations available:

1. **Combined MCP Server (Recommended)**: 
   - `combined_mcp_server.py` - Direct implementation that uses stdin/stdout for communication
   - `run-combined-server.sh` - Wrapper script for the combined server

2. **Socket-based Servers**:
   - `daemon_mcp_server.py` - Background server that receives commands via socket connection
   - `socket_proxy.py` - Proxy that forwards commands from stdin to the daemon server and back
   
3. **Standalone Server**:
   - `standalone-mcp-server.py` - Original standalone implementation
   - `run-python-server.sh` - Wrapper script for the standalone server

## Setup Instructions

### 1. Set up Claude Desktop

1. Install Claude Desktop if you haven't already
2. Configure the MCP server connection in Claude Desktop settings

### 2. Run the Server

#### Option 1: Combined Server (Recommended)

```bash
./run-combined-server.sh
```

This runs a direct server that communicates with Claude via stdin/stdout without any intermediate sockets.

#### Option 2: Socket-based Server

```bash
# First, start the daemon server
./daemon_mcp_server.py

# Then, in Claude Desktop settings, point to:
./socket_proxy.py
```

This uses a socket-based approach with a persistent background daemon and a socket proxy.

#### Option 3: Standalone Server

```bash
./run-python-server.sh
```

This runs the original standalone server implementation.

## Available Tools

The server provides several tools for 3D modeling:

1. **geometry_tools.create_sphere** - Create a sphere with specified center and radius
2. **geometry_tools.create_box** - Create a box with specified dimensions
3. **geometry_tools.create_cylinder** - Create a cylinder with specified parameters
4. **scene_tools.get_scene_info** - Get information about the current scene
5. **scene_tools.clear_scene** - Clear objects from the scene
6. **scene_tools.create_layer** - Create a new layer in the document

## Troubleshooting

If you encounter connection issues:

1. Make sure no old servers are running:
   ```bash
   pkill -f "combined_mcp_server.py|daemon_mcp_server.py|socket_proxy.py|standalone-mcp_server.py"
   ```

2. Check the log files:
   - `combined_mcp_server.log` - For the combined server
   - `daemon_mcp_server.log` - For the daemon server
   - `socket_proxy.log` - For the socket proxy

3. Restart Claude Desktop completely

## License

This project is released under the MIT License. See the LICENSE file for details. 

## Improved Logging System

The system now features a unified logging framework that centralizes logs from all components:

- Server logs
- Plugin logs
- Claude AI logs
- Diagnostic logs

All logs follow a consistent format and are stored in the `logs/` directory with separate subdirectories for each component.

### Log Management

A log management tool is provided that offers powerful capabilities for viewing, monitoring, and analyzing logs:

```bash
# View logs
./log_manager.py view

# Monitor logs in real-time
./log_manager.py monitor

# View errors with context
./log_manager.py errors

# Generate error reports
./log_manager.py report
```

For detailed information on using the logging system, see [LOGGING.md](LOGGING.md).

## Development

### Project Structure

- `combined_mcp_server.py`: Main MCP server implementation
- `diagnose_rhino_connection.py`: Diagnostic tool for testing Rhino connection
- `log_manager.py`: Tool for managing and analyzing logs
- `run-combined-server.sh`: Script to start the MCP server
- `logs/`: Directory containing all logs

### Adding New Features

1. Add new tools as methods in the `combined_mcp_server.py` file
2. Use the existing logging framework for consistent error handling
3. Update diagnostic tools if needed 