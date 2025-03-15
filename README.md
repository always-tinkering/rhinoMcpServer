# RhinoMCP Server

A minimal Model Context Protocol (MCP) server that exposes Rhino 3D's Python scripting capabilities to AI systems. This server enables AI agents to generate, manipulate, and analyze 3D models in Rhino through a standardized protocol with proper user consent.

## Features

- **Scene Context**: Get information about all objects in the current Rhino document
- **Object Creation**: Create basic 3D geometry (currently supports spheres)
- **User Consent**: All operations require explicit user approval
- **Error Handling**: Robust error handling for Rhino operations
- **Security**: Following MCP security guidelines for user consent

## Requirements

- Rhino 8 with Python 3.8+
- Python packages specified in `requirements.txt`

## Installation

1. Clone this repository or download the files
2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

3. Make sure Rhino 8 is installed with Python support

## Usage

### Running the Server

The server is designed to be started from within Rhino's Python environment:

1. Open Rhino 8
2. Run the Python script command
3. Navigate to and run `rhinomcp_server.py`

You can also run the server from a Python environment with Rhino libraries accessible:

```bash
python rhinomcp_server.py
```

### Integration with AI Systems

This MCP server uses the STDIO transport protocol, which means it can be easily integrated with AI systems that support the Model Context Protocol.

For Claude AI integration, add the following to your configuration:

```json
{
  "mcpServers": {
    "rhino": {
      "command": "python",
      "args": ["path/to/rhinomcp_server.py"]
    }
  }
}
```

## Available Tools

### Scene Context

To get information about all objects in the current Rhino document:

```python
# Example of requesting scene context resource
resource = await mcp.get_resource("scene")
```

The response includes:
- Object count
- List of all objects with their properties (ID, type, layer, color, position, bounding box)
- Active view
- Available layers

### Create Sphere

To create a sphere in the Rhino document:

```python
# Example of calling the create_sphere tool
result = await mcp.call_tool("create_sphere", {
    "center_x": 0.0,
    "center_y": 0.0,
    "center_z": 0.0,
    "radius": 5.0,
    "color": "#FF0000"  # Optional
})
```

Each creation operation will prompt the user for consent via a dialog in Rhino.

## Security Considerations

- All operations that modify the Rhino document require explicit user consent
- Operations are logged for auditing
- The server runs with the same permissions as the Rhino process

## Error Handling

The server provides detailed error messages for failed operations, including:
- Invalid parameters
- Rhino operation failures
- User consent denials

## Extending the Server

To add new tools or resources:

1. Create new Pydantic models for parameters and results
2. Add helper functions for Rhino operations
3. Register new resource handlers with `@mcp.resource_handler()`
4. Register new tools with `@mcp.tool()`

## Troubleshooting

- **Import Errors**: Make sure you're running the server within Rhino's Python environment
- **Connection Issues**: Check that the STDIO channels are properly connected
- **Operation Failures**: Check the server logs for detailed error messages

## License

This project is available under the MIT License.

## Acknowledgements

- Rhino 3D and McNeel for the Rhino API
- The Model Context Protocol (MCP) team for the protocol specification 