#!/usr/bin/env python3
"""
Combined MCP Server for Rhino
This script implements a direct MCP server using the FastMCP pattern,
following the Model Context Protocol specification.
"""

import json
import os
import sys
import time
import logging
import signal
import threading
import traceback
from datetime import datetime
import re
import uuid
import asyncio
import socket
from typing import Dict, Any, List, Optional, Tuple
from contextlib import asynccontextmanager
from typing import AsyncIterator

# Import the FastMCP class
from mcp.server.fastmcp import FastMCP, Context

# Configure logging - improved with structured format and unified location
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(log_dir, exist_ok=True)

# Create log subdirectories
server_log_dir = os.path.join(log_dir, "server")
plugin_log_dir = os.path.join(log_dir, "plugin")
claude_log_dir = os.path.join(log_dir, "claude")

for directory in [server_log_dir, plugin_log_dir, claude_log_dir]:
    os.makedirs(directory, exist_ok=True)

# Log filenames based on date for easier archiving
today = datetime.now().strftime("%Y-%m-%d")
server_log_file = os.path.join(server_log_dir, f"server_{today}.log")
debug_log_file = os.path.join(server_log_dir, f"debug_{today}.log")

# Set up the logger with custom format including timestamp, level, component, and message
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] [%(component)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr),
        logging.FileHandler(server_log_file)
    ]
)

# Add a filter to add the component field
class ComponentFilter(logging.Filter):
    def __init__(self, component="server"):
        super().__init__()
        self.component = component

    def filter(self, record):
        record.component = self.component
        return True

# Get logger and add the component filter
logger = logging.getLogger()
logger.addFilter(ComponentFilter())

# Add a debug file handler for detailed debugging
debug_handler = logging.FileHandler(debug_log_file)
debug_handler.setLevel(logging.DEBUG)
debug_handler.setFormatter(logging.Formatter('[%(asctime)s] [%(levelname)s] [%(component)s] %(message)s'))
logger.addHandler(debug_handler)

# Log basic server startup information
logger.info(f"RhinoMCP server starting in {os.getcwd()}")
logger.info(f"Log files directory: {log_dir}")
logger.info(f"Server log file: {server_log_file}")
logger.info(f"Debug log file: {debug_log_file}")

# Create a PID file to track this process
pid_file = os.path.join(log_dir, "combined_server.pid")
with open(pid_file, "w") as f:
    f.write(str(os.getpid()))
logger.info(f"Server PID: {os.getpid()}")

# Global Rhino connection
_rhino_connection = None

class RhinoConnection:
    """Class to manage socket connection to Rhino plugin"""
    
    def __init__(self, host: str = "localhost", port: int = 9876):
        self.host = host
        self.port = port
        self.sock = None
        self.request_id = 0
    
    def connect(self) -> bool:
        """Connect to the Rhino plugin socket server"""
        if self.sock:
            return True
            
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            logger.info(f"Connected to Rhino at {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Rhino: {str(e)}")
            logger.debug(f"Connection error details: {traceback.format_exc()}")
            self.sock = None
            return False
    
    def disconnect(self):
        """Disconnect from the Rhino plugin"""
        if self.sock:
            try:
                self.sock.close()
            except Exception as e:
                logger.error(f"Error disconnecting from Rhino: {str(e)}")
            finally:
                self.sock = None
    
    def send_command(self, command_type: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send a command to Rhino and return the response"""
        if not self.sock and not self.connect():
            raise ConnectionError("Not connected to Rhino")
        
        # Increment request ID for tracking
        self.request_id += 1
        current_request_id = self.request_id
        
        command = {
            "id": current_request_id,
            "type": command_type,
            "params": params or {}
        }
        
        try:
            # Log the command being sent
            logger.info(f"Request #{current_request_id}: Sending command '{command_type}' to Rhino")
            logger.debug(f"Request #{current_request_id} Parameters: {json.dumps(params or {})}")
            
            # Send the command
            command_json = json.dumps(command)
            logger.debug(f"Request #{current_request_id} Raw command: {command_json}")
            self.sock.sendall(command_json.encode('utf-8'))
            
            # Set a timeout for receiving
            self.sock.settimeout(10.0)
            
            # Receive the response
            buffer_size = 4096
            response_data = b""
            
            while True:
                chunk = self.sock.recv(buffer_size)
                if not chunk:
                    break
                response_data += chunk
                
                # Try to parse as JSON to see if we have a complete response
                try:
                    json.loads(response_data.decode('utf-8'))
                    # If parsing succeeds, we have a complete response
                    break
                except json.JSONDecodeError:
                    # Not a complete JSON yet, continue receiving
                    continue
            
            if not response_data:
                logger.error(f"Request #{current_request_id}: No data received from Rhino")
                raise ConnectionError(f"Request #{current_request_id}: No data received from Rhino")
            
            # Log the raw response for debugging
            raw_response = response_data.decode('utf-8')
            logger.debug(f"Request #{current_request_id} Raw response: {raw_response}")
            
            response = json.loads(raw_response)
            
            # Check if the response indicates an error
            if "error" in response:
                error_msg = response.get("error", "Unknown error from Rhino")
                logger.error(f"Request #{current_request_id}: Rhino reported error: {error_msg}")
                raise Exception(f"Request #{current_request_id}: Rhino error: {error_msg}")
            
            if response.get("status") == "error":
                error_msg = response.get("message", "Unknown error from Rhino")
                logger.error(f"Request #{current_request_id}: Rhino reported error status: {error_msg}")
                raise Exception(f"Request #{current_request_id}: Rhino error: {error_msg}")
            
            # Log success
            logger.info(f"Request #{current_request_id}: Command '{command_type}' executed successfully")
            
            # If we get here, assume success and return the result
            if "result" in response:
                return response.get("result", {})
            else:
                # If there's no result field but no error either, return the whole response
                return response
        except socket.timeout:
            logger.error(f"Request #{current_request_id}: Socket timeout while waiting for response from Rhino")
            logger.debug(f"Request #{current_request_id}: Timeout after 10 seconds waiting for response to '{command_type}'")
            self.sock = None
            raise Exception(f"Request #{current_request_id}: Timeout waiting for Rhino response")
        except (ConnectionError, BrokenPipeError, ConnectionResetError) as e:
            logger.error(f"Request #{current_request_id}: Socket connection error: {str(e)}")
            self.sock = None
            raise Exception(f"Request #{current_request_id}: Connection to Rhino lost: {str(e)}")
        except json.JSONDecodeError as e:
            logger.error(f"Request #{current_request_id}: Invalid JSON response: {str(e)}")
            if 'response_data' in locals():
                logger.error(f"Request #{current_request_id}: Raw response causing JSON error: {response_data[:200]}")
            self.sock = None
            raise Exception(f"Request #{current_request_id}: Invalid JSON response from Rhino: {str(e)}")
        except Exception as e:
            logger.error(f"Request #{current_request_id}: Error communicating with Rhino: {str(e)}")
            logger.error(f"Request #{current_request_id}: Traceback: {traceback.format_exc()}")
            self.sock = None
            raise Exception(f"Request #{current_request_id}: Communication error with Rhino: {str(e)}")

def get_rhino_connection() -> RhinoConnection:
    """Get or create a connection to Rhino"""
    global _rhino_connection
    
    # If we have an existing connection, check if it's still valid
    if _rhino_connection is not None:
        try:
            # Don't use ping as it's not implemented in the Rhino plugin
            # Instead, try get_scene_info which is more likely to work
            _rhino_connection.send_command("get_scene_info", {})
            return _rhino_connection
        except Exception as e:
            # Connection is dead, close it and create a new one
            logger.warning(f"Existing connection is no longer valid: {str(e)}")
            try:
                _rhino_connection.disconnect()
            except:
                pass
            _rhino_connection = None
    
    # Create a new connection if needed
    if _rhino_connection is None:
        _rhino_connection = RhinoConnection()
        if not _rhino_connection.connect():
            logger.error("Failed to connect to Rhino")
            _rhino_connection = None
            raise Exception("Could not connect to Rhino. Make sure the Rhino plugin is running.")
        
        # Verify connection with a known working command
        try:
            # Test the connection with get_scene_info command
            result = _rhino_connection.send_command("get_scene_info", {})
            logger.info(f"Connection test successful: {result}")
        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            _rhino_connection.disconnect()
            _rhino_connection = None
            raise Exception(f"Rhino plugin connection test failed: {str(e)}")
            
        logger.info("Created new connection to Rhino")
    
    return _rhino_connection

# Server lifecycle management
@asynccontextmanager
async def server_lifespan(server: FastMCP) -> AsyncIterator[Dict[str, Any]]:
    """Manage server startup and shutdown lifecycle"""
    try:
        logger.info("RhinoMCP server starting up")
        
        # Try to connect to Rhino on startup to verify it's available
        try:
            # This will initialize the global connection if needed
            rhino = get_rhino_connection()
            logger.info("Successfully connected to Rhino on startup")
        except Exception as e:
            logger.warning(f"Could not connect to Rhino on startup: {str(e)}")
            logger.warning("Make sure the Rhino plugin is running before using Rhino resources or tools")
        
        yield {}  # No context resources needed for now
    finally:
        logger.info("RhinoMCP server shutting down")
        # Cleanup code
        global _rhino_connection
        if _rhino_connection:
            logger.info("Disconnecting from Rhino on shutdown")
            _rhino_connection.disconnect()
            _rhino_connection = None
            
        if os.path.exists(pid_file):
            os.remove(pid_file)
            logger.info("Removed PID file")

# Initialize the FastMCP server
mcp = FastMCP(
    "RhinoMcpServer",
    description="A Model Context Protocol server for Rhino 3D",
    lifespan=server_lifespan
)

# Tool implementations using FastMCP decorators

@mcp.tool()
def create_sphere(
    ctx: Context,
    centerX: float,
    centerY: float,
    centerZ: float,
    radius: float,
    color: Optional[str] = None
) -> str:
    """
    Creates a sphere with the specified center and radius.
    
    Parameters:
    - centerX: X coordinate of the sphere center
    - centerY: Y coordinate of the sphere center
    - centerZ: Z coordinate of the sphere center
    - radius: Radius of the sphere
    - color: Optional color for the sphere (e.g., 'red', 'blue', etc.)
    
    Returns:
    A message indicating the created sphere details
    """
    tool_id = str(uuid.uuid4())[:8]  # Generate a short ID for tracking this tool call
    logger.info(f"[{tool_id}] Tool call: create_sphere with center=({centerX},{centerY},{centerZ}), radius={radius}, color={color}")
    
    try:
        # Get the Rhino connection
        rhino = get_rhino_connection()
        
        # Send the command to Rhino
        params = {
            "centerX": centerX,
            "centerY": centerY,
            "centerZ": centerZ,
            "radius": radius
        }
        
        if color:
            params["color"] = color
            
        result = rhino.send_command("create_sphere", params)
        
        # Log success
        logger.info(f"[{tool_id}] Sphere created successfully")
        
        # Return the result
        return json.dumps(result)
    except Exception as e:
        logger.error(f"[{tool_id}] Error creating sphere: {str(e)}")
        logger.error(f"[{tool_id}] Traceback: {traceback.format_exc()}")
        return json.dumps({
            "success": False,
            "error": f"Error creating sphere: {str(e)}"
        })

@mcp.tool()
def create_box(
    ctx: Context,
    cornerX: float,
    cornerY: float,
    cornerZ: float,
    width: float,
    depth: float,
    height: float,
    color: Optional[str] = None
) -> str:
    """
    Creates a box with the specified dimensions.
    
    Parameters:
    - cornerX: X coordinate of the box corner
    - cornerY: Y coordinate of the box corner
    - cornerZ: Z coordinate of the box corner
    - width: Width of the box (X dimension)
    - depth: Depth of the box (Y dimension)
    - height: Height of the box (Z dimension)
    - color: Optional color for the box (e.g., 'red', 'blue', etc.)
    
    Returns:
    A message indicating the created box details
    """
    tool_id = str(uuid.uuid4())[:8]  # Generate a short ID for tracking this tool call
    logger.info(f"[{tool_id}] Tool call: create_box at ({cornerX},{cornerY},{cornerZ}), size={width}x{depth}x{height}, color={color}")
    
    try:
        # Get the Rhino connection
        rhino = get_rhino_connection()
        
        # Send the command to Rhino
        params = {
            "cornerX": cornerX,
            "cornerY": cornerY,
            "cornerZ": cornerZ,
            "width": width,
            "depth": depth,
            "height": height
        }
        
        if color:
            params["color"] = color
            
        result = rhino.send_command("create_box", params)
        
        # Log success
        logger.info(f"[{tool_id}] Box created successfully")
        
        # Return the result
        return json.dumps(result)
    except Exception as e:
        logger.error(f"[{tool_id}] Error creating box: {str(e)}")
        logger.error(f"[{tool_id}] Traceback: {traceback.format_exc()}")
        return json.dumps({
            "success": False,
            "error": f"Error creating box: {str(e)}",
            "toolId": tool_id  # Include the tool ID for error tracking
        })

@mcp.tool()
def create_cylinder(
    ctx: Context,
    baseX: float,
    baseY: float,
    baseZ: float,
    height: float,
    radius: float,
    color: Optional[str] = None
) -> str:
    """
    Creates a cylinder with the specified base point, height, and radius.
    
    Parameters:
    - baseX: X coordinate of the cylinder base point
    - baseY: Y coordinate of the cylinder base point
    - baseZ: Z coordinate of the cylinder base point
    - height: Height of the cylinder
    - radius: Radius of the cylinder
    - color: Optional color for the cylinder (e.g., 'red', 'blue', etc.)
    
    Returns:
    A message indicating the created cylinder details
    """
    tool_id = str(uuid.uuid4())[:8]  # Generate a short ID for tracking this tool call
    logger.info(f"[{tool_id}] Tool call: create_cylinder at ({baseX},{baseY},{baseZ}), height={height}, radius={radius}, color={color}")
    
    try:
        # Get the Rhino connection
        rhino = get_rhino_connection()
        
        # Send the command to Rhino
        params = {
            "baseX": baseX,
            "baseY": baseY,
            "baseZ": baseZ,
            "height": height,
            "radius": radius
        }
        
        if color:
            params["color"] = color
            
        result = rhino.send_command("create_cylinder", params)
        
        # Log success
        logger.info(f"[{tool_id}] Cylinder created successfully")
        
        # Return the result
        return json.dumps(result)
    except Exception as e:
        logger.error(f"[{tool_id}] Error creating cylinder: {str(e)}")
        logger.error(f"[{tool_id}] Traceback: {traceback.format_exc()}")
        return json.dumps({
            "success": False,
            "error": f"Error creating cylinder: {str(e)}",
            "toolId": tool_id  # Include the tool ID for error tracking
        })

@mcp.tool()
def get_scene_info(ctx: Context) -> str:
    """
    Gets information about objects in the current scene.
    
    Returns:
    A JSON string containing scene information
    """
    tool_id = str(uuid.uuid4())[:8]  # Generate a short ID for tracking this tool call
    logger.info(f"[{tool_id}] Tool call: get_scene_info")
    
    try:
        # Get the Rhino connection
        rhino = get_rhino_connection()
        
        # Send the command to Rhino
        result = rhino.send_command("get_scene_info", {})
        
        # Log success
        logger.info(f"[{tool_id}] Scene info retrieved successfully")
        
        # Return the result
        return json.dumps(result)
    except Exception as e:
        logger.error(f"[{tool_id}] Error getting scene info: {str(e)}")
        logger.error(f"[{tool_id}] Traceback: {traceback.format_exc()}")
        return json.dumps({
            "success": False,
            "error": f"Error getting scene info: {str(e)}",
            "toolId": tool_id  # Include the tool ID for error tracking
        })

@mcp.tool()
def clear_scene(ctx: Context, currentLayerOnly: bool = False) -> str:
    """
    Clears all objects from the current scene.
    
    Parameters:
    - currentLayerOnly: If true, only delete objects on the current layer
    
    Returns:
    A message indicating the operation result
    """
    tool_id = str(uuid.uuid4())[:8]  # Generate a short ID for tracking this tool call
    layer_info = "current layer only" if currentLayerOnly else "all layers"
    logger.info(f"[{tool_id}] Tool call: clear_scene ({layer_info})")
    
    try:
        # Get the Rhino connection
        rhino = get_rhino_connection()
        
        # Send the command to Rhino
        params = {
            "currentLayerOnly": currentLayerOnly
        }
        
        result = rhino.send_command("clear_scene", params)
        
        # Log success
        logger.info(f"[{tool_id}] Scene cleared successfully ({layer_info})")
        
        # Return the result
        return json.dumps(result)
    except Exception as e:
        logger.error(f"[{tool_id}] Error clearing scene: {str(e)}")
        logger.error(f"[{tool_id}] Traceback: {traceback.format_exc()}")
        return json.dumps({
            "success": False,
            "error": f"Error clearing scene: {str(e)}",
            "toolId": tool_id  # Include the tool ID for error tracking
        })

@mcp.tool()
def create_layer(ctx: Context, name: str, color: Optional[str] = None) -> str:
    """
    Creates a new layer in the Rhino document.
    
    Parameters:
    - name: Name of the new layer
    - color: Optional color for the layer (e.g., 'red', 'blue', etc.)
    
    Returns:
    A message indicating the operation result
    """
    tool_id = str(uuid.uuid4())[:8]  # Generate a short ID for tracking this tool call
    color_info = f" with color {color}" if color else ""
    logger.info(f"[{tool_id}] Tool call: create_layer '{name}'{color_info}")
    
    try:
        # Get the Rhino connection
        rhino = get_rhino_connection()
        
        # Send the command to Rhino
        params = {
            "name": name
        }
        
        if color:
            params["color"] = color
            
        result = rhino.send_command("create_layer", params)
        
        # Log success
        logger.info(f"[{tool_id}] Layer '{name}' created successfully")
        
        # Return the result
        return json.dumps(result)
    except Exception as e:
        logger.error(f"[{tool_id}] Error creating layer: {str(e)}")
        logger.error(f"[{tool_id}] Traceback: {traceback.format_exc()}")
        return json.dumps({
            "success": False,
            "error": f"Error creating layer: {str(e)}",
            "toolId": tool_id  # Include the tool ID for error tracking
        })

# Record Claude interactions to debug context issues
@mcp.tool()
def log_claude_message(
    ctx: Context,
    message: str,
    type: str = "info"
) -> str:
    """
    Log a message from Claude for debugging purposes.
    
    Parameters:
    - message: The message to log
    - type: The type of message (info, error, warning, debug)
    
    Returns:
    Success confirmation
    """
    log_id = str(uuid.uuid4())[:8]
    
    # Create a timestamp for the filename
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    claude_log_file = os.path.join(claude_log_dir, f"claude_{timestamp}_{log_id}.log")
    
    try:
        with open(claude_log_file, "w") as f:
            f.write(message)
        
        # Log to server log as well
        if type == "error":
            logger.error(f"[Claude] [{log_id}] {message[:100]}...")
        elif type == "warning":
            logger.warning(f"[Claude] [{log_id}] {message[:100]}...")
        elif type == "debug":
            logger.debug(f"[Claude] [{log_id}] {message[:100]}...")
        else:
            logger.info(f"[Claude] [{log_id}] {message[:100]}...")
        
        return json.dumps({
            "success": True,
            "logId": log_id,
            "logFile": claude_log_file
        })
    except Exception as e:
        logger.error(f"Error logging Claude message: {str(e)}")
        return json.dumps({
            "success": False,
            "error": f"Error logging Claude message: {str(e)}"
        })

def main():
    """Main function to run the MCP server"""
    logger.info("=== RhinoMCP Server Starting ===")
    logger.info(f"Process ID: {os.getpid()}")
    
    try:
        # Run the FastMCP server
        mcp.run()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.error(f"Error running server: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
    finally:
        logger.info("Server shutting down...")
        
        # Clean up connection
        global _rhino_connection
        if _rhino_connection:
            _rhino_connection.disconnect()
        
        if os.path.exists(pid_file):
            os.remove(pid_file)
            logger.info("Removed PID file")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 