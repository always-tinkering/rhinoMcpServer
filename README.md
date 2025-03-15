
# RhinoMCP - Rhino Model Context Protocol Integration

RhinoMCP connects Rhino to Claude AI through the Model Context Protocol (MCP), allowing Claude to directly interact with and control Rhino. This integration enables prompt assisted 3D modeling, architectural design, and geometry manipulation.

## Features

* **Two-way communication**: Connect Claude AI to Rhino through a socket-based server
* **Geometry manipulation**: Create, modify, and delete 3D objects in Rhino
* **Material control**: Apply and modify materials and colors
* **Scene inspection**: Get detailed information about the current Rhino scene
* **Code execution**: Run arbitrary Python code in Rhino from Claude

## Components

The system consists of two main components:

1. **Rhino Plugin (`plugin.py`)**: A Rhino plugin that creates a socket server within Rhino to receive and execute commands
2. **MCP Server (`src/rhino_mcp/server.py`)**: A Python server that implements the Model Context Protocol and connects to the Rhino plugin

## Installation

### Prerequisites

* Rhino 7 or newer
* Python 3.10 or newer

### Quick Start

Run rhino-mcp without installing it permanently (uvx will automatically download and run the package):

```bash
uvx rhino-mcp
```

If you're on Mac, please install uv as

```bash
brew install uv
```

Otherwise installation instructions are on their website: [Install uv](https://github.com/astral-sh/uv)

### Claude for Desktop Integration

Update your `claude_desktop_config.json` (located in `~/Library/Application\ Support/Claude/claude_desktop_config.json` on macOS and `%APPDATA%/Claude/claude_desktop_config.json` on Windows) to include the following:

```json
{
    "mcpServers": {
        "rhino": {
            "command": "uvx",
            "args": [
                "rhino-mcp"
            ]
        }
    }
}
```

### Installing the Rhino Plugin

1. Download the `plugin.py` file from this repo
2. Open Rhino
3. Go to Tools > PythonScript > Edit
4. Place the plugin in your Rhino Python scripts folder
5. Restart Rhino

## Usage

### Starting the Connection

1. In Rhino, type `StartMCPServer` in the command line
2. Set the port number (default: 9877)
3. Make sure the MCP server is running in your terminal

### Using with Claude

Once connected, Claude can interact with Rhino using the following capabilities:

#### Tools

* `get_scene_info` - Gets scene information
* `get_object_info` - Gets detailed information for a specific object in the scene
* `create_primitive` - Create basic primitive objects with optional color
* `set_object_property` - Set a single property of an object
* `create_object` - Create a new object with detailed parameters
* `modify_object` - Modify an existing object's properties
* `delete_object` - Remove an object from the scene
* `set_material` - Apply or create materials for objects
* `execute_rhino_code` - Run any Python code in Rhino

### Example Commands

Here are some examples of what you can ask Claude to do:

* "Create a parametric facade with a grid of windows"
* "Generate a spiral staircase with custom parameters"
* "Create a site plan from imported GIS data"
* "Apply materials to selected surfaces"
* "Create a section cut through the model"
* "Set up standard architectural views"
* "Export the model for visualization"

## Troubleshooting

* **Connection issues**: Make sure both the Rhino plugin server and the MCP server are running
* **Command failures**: Check the command line in Rhino for error messages
* **Timeout errors**: Try simplifying your requests or breaking them into smaller steps

## Technical Details

### Communication Protocol

The system uses a simple JSON-based protocol over TCP sockets:

* **Commands** are sent as JSON objects with a `type` and optional `params`
* **Responses** are JSON objects with a `status` and `result` or `message`

## Limitations & Security Considerations

* The `execute_rhino_code` tool allows running arbitrary Python code in Rhino, which can be powerful but potentially dangerous. Use with caution in production environments. ALWAYS save your work before using it.
* Complex operations might need to be broken down into smaller steps

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Disclaimer

This is a third-party integration and not made by Rhino. 