#!/usr/bin/env python3
"""
Standalone MCP Server for Rhino
This script implements a direct MCP server that communicates with both Claude and Rhino
without any complex piping or shell scripts.
"""

import json
import os
import socket
import sys
import time
import logging
import signal
import threading
import traceback
from datetime import datetime

# Configure logging to stderr and file
log_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(log_dir)
log_file = os.path.join(root_dir, "logs", "standalone_mcp_server.log")
os.makedirs(os.path.dirname(log_file), exist_ok=True)

# Configure logging to stderr only
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr),
        logging.FileHandler(log_file)
    ]
)

# Global variables
EXIT_FLAG = False
SERVER_STATE = "waiting"  # States: waiting, initialized, processing

# Create a PID file
pid_file = os.path.join(root_dir, "logs", "standalone_server.pid")
with open(pid_file, "w") as f:
    f.write(str(os.getpid()))

def send_json_response(data):
    """Send a JSON response to stdout (Claude)"""
    try:
        # Ensure we're sending a valid JSON object
        json_str = json.dumps(data)
        
        # Write as plain text to stdout
        print(json_str, flush=True)
        
        logging.debug(f"Sent JSON response: {json_str[:100]}...")
    except Exception as e:
        logging.error(f"Error sending JSON: {str(e)}")

def handle_initialize(request):
    """Handle the initialize request and return server capabilities"""
    logging.info("Processing initialize request")
    
    # Get request ID from the client (default to 0 if not provided)
    request_id = request.get("id", 0)
    
    # Return hard-coded initialization response with tools
    response = {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "serverInfo": {
                "name": "RhinoMcpServer",
                "version": "0.1.0"
            },
            "capabilities": {
                "tools": [
                    {
                        "name": "geometry_tools.create_sphere",
                        "description": "Creates a sphere with the specified center and radius",
                        "parameters": [
                            {"name": "centerX", "description": "X coordinate of the sphere center", "required": True, "schema": {"type": "number"}},
                            {"name": "centerY", "description": "Y coordinate of the sphere center", "required": True, "schema": {"type": "number"}},
                            {"name": "centerZ", "description": "Z coordinate of the sphere center", "required": True, "schema": {"type": "number"}},
                            {"name": "radius", "description": "Radius of the sphere", "required": True, "schema": {"type": "number"}},
                            {"name": "color", "description": "Optional color for the sphere (e.g., 'red', 'blue', etc.)", "required": False, "schema": {"type": "string"}}
                        ]
                    },
                    {
                        "name": "geometry_tools.create_box",
                        "description": "Creates a box with the specified dimensions",
                        "parameters": [
                            {"name": "cornerX", "description": "X coordinate of the box corner", "required": True, "schema": {"type": "number"}},
                            {"name": "cornerY", "description": "Y coordinate of the box corner", "required": True, "schema": {"type": "number"}},
                            {"name": "cornerZ", "description": "Z coordinate of the box corner", "required": True, "schema": {"type": "number"}},
                            {"name": "width", "description": "Width of the box (X dimension)", "required": True, "schema": {"type": "number"}},
                            {"name": "depth", "description": "Depth of the box (Y dimension)", "required": True, "schema": {"type": "number"}},
                            {"name": "height", "description": "Height of the box (Z dimension)", "required": True, "schema": {"type": "number"}},
                            {"name": "color", "description": "Optional color for the box (e.g., 'red', 'blue', etc.)", "required": False, "schema": {"type": "string"}}
                        ]
                    },
                    {
                        "name": "geometry_tools.create_cylinder",
                        "description": "Creates a cylinder with the specified base point, height, and radius",
                        "parameters": [
                            {"name": "baseX", "description": "X coordinate of the cylinder base point", "required": True, "schema": {"type": "number"}},
                            {"name": "baseY", "description": "Y coordinate of the cylinder base point", "required": True, "schema": {"type": "number"}},
                            {"name": "baseZ", "description": "Z coordinate of the cylinder base point", "required": True, "schema": {"type": "number"}},
                            {"name": "height", "description": "Height of the cylinder", "required": True, "schema": {"type": "number"}},
                            {"name": "radius", "description": "Radius of the cylinder", "required": True, "schema": {"type": "number"}},
                            {"name": "color", "description": "Optional color for the cylinder (e.g., 'red', 'blue', etc.)", "required": False, "schema": {"type": "string"}}
                        ]
                    },
                    {
                        "name": "scene_tools.get_scene_info",
                        "description": "Gets information about objects in the current scene",
                        "parameters": []
                    },
                    {
                        "name": "scene_tools.clear_scene",
                        "description": "Clears all objects from the current scene",
                        "parameters": [
                            {"name": "currentLayerOnly", "description": "If true, only delete objects on the current layer", "required": False, "schema": {"type": "boolean"}}
                        ]
                    },
                    {
                        "name": "scene_tools.create_layer",
                        "description": "Creates a new layer in the Rhino document",
                        "parameters": [
                            {"name": "name", "description": "Name of the new layer", "required": True, "schema": {"type": "string"}},
                            {"name": "color", "description": "Optional color for the layer (e.g., 'red', 'blue', etc.)", "required": False, "schema": {"type": "string"}}
                        ]
                    }
                ]
            }
        }
    }
    
    # Mark server as initialized
    global SERVER_STATE
    SERVER_STATE = "initialized"
    logging.info("Server initialized successfully")
    
    return response

def handle_tool_call(request):
    """Handle a tool call request"""
    tool_name = request["params"]["name"]
    parameters = request["params"]["parameters"]
    request_id = request.get("id", 0)
    
    logging.info(f"Executing tool: {tool_name}")
    
    # Here you would actually implement the tool functionality
    # For this example, we just return a dummy success response
    response = {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "result": {"success": True, "message": f"Executed {tool_name} with parameters {parameters}"}
        }
    }
    
    return response

def handle_shutdown(request):
    """Handle a shutdown request"""
    request_id = request.get("id", 0)
    logging.info("Shutdown requested")
    
    global EXIT_FLAG
    EXIT_FLAG = True
    
    response = {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {"success": True}
    }
    
    return response

def process_message(message):
    """Process a single message from the client."""
    try:
        method = message.get("method", "")
        
        if method == "initialize":
            response = handle_initialize(message)
            send_json_response(response)
            return True
        elif method == "tools/call":
            response = handle_tool_call(message)
            send_json_response(response)
            return True
        elif method == "shutdown":
            response = handle_shutdown(message)
            send_json_response(response)
            return False
        elif method == "notifications/cancelled":
            # Just acknowledge and continue
            logging.info("Received cancellation notification")
            return True
        else:
            logging.warning(f"Unknown method: {method}")
            return True
    except Exception as e:
        logging.error(f"Error processing message: {e}")
        traceback.print_exc(file=sys.stderr)
        return True  # Keep running even on errors

def cleanup():
    """Clean up resources when exiting"""
    try:
        if os.path.exists(pid_file):
            os.remove(pid_file)
            logging.info("Removed PID file")
    except Exception as e:
        logging.error(f"Error in cleanup: {str(e)}")

def signal_handler(sig, frame):
    """Handle termination signals"""
    global EXIT_FLAG, SERVER_STATE
    
    logging.info(f"Received signal {sig}")
    
    # If we're initialized, ignore SIGTERM (15) and stay alive
    if SERVER_STATE == "initialized" and sig == signal.SIGTERM:
        logging.info(f"Server is initialized - ignoring SIGTERM and staying alive")
        return
        
    # Otherwise, exit normally
    logging.info(f"Initiating shutdown...")
    EXIT_FLAG = True

def main():
    """Main function"""
    global EXIT_FLAG
    
    # Register signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Register cleanup handler
    import atexit
    atexit.register(cleanup)
    
    logging.info("=== MCP Server Starting ===")
    logging.info(f"Process ID: {os.getpid()}")
    
    try:
        # Main loop
        while not EXIT_FLAG:
            try:
                # Read a line from stdin
                line = input()
                if not line:
                    time.sleep(0.1)
                    continue
                
                # Parse the JSON message
                try:
                    message = json.loads(line)
                    # Process the message
                    if not process_message(message):
                        break
                except json.JSONDecodeError as e:
                    logging.error(f"Invalid JSON received: {e}")
                    continue
            except EOFError:
                # If we're initialized, keep running even if stdin is closed
                if SERVER_STATE == "initialized":
                    logging.info("Stdin closed but server is initialized - staying alive")
                    # Sleep to avoid tight loop if stdin is permanently closed
                    time.sleep(5)
                    continue
                else:
                    logging.info("Stdin closed, exiting...")
                    break
            except Exception as e:
                logging.error(f"Error in main loop: {e}")
                traceback.print_exc(file=sys.stderr)
                time.sleep(1)
    finally:
        logging.info("Server shutting down...")
        cleanup()

if __name__ == "__main__":
    main() 