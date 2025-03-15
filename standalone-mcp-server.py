#!/usr/bin/env python3
"""
Standalone MCP Server for Rhino
This script implements a direct MCP server that communicates with both Claude and Rhino
without any complex piping or shell scripts.
"""

import json
import os
import socket
import subprocess
import sys
import time
import logging
import signal
from datetime import datetime
from threading import Thread, Lock

# Configure logging
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(log_dir, exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = os.path.join(log_dir, f"standalone_server_{timestamp}.log")

logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stderr)
    ]
)

# Global variables
SERVER_PROCESS = None
SERVER_LOCK = Lock()
RHINO_PORT = 9876
EXIT_FLAG = False

def send_json_response(data):
    """Send a JSON response to stdout (Claude)"""
    try:
        # Ensure it's valid JSON first
        if isinstance(data, str):
            json_obj = json.loads(data)  # Parse to validate
            json_str = data  # Use the original string
        else:
            json_str = json.dumps(data)  # Convert dict to string
        
        # Write to stdout without any extra characters
        sys.stdout.write(json_str + "\n")
        sys.stdout.flush()
        logging.debug(f"Sent JSON: {json_str[:100]}...")
    except Exception as e:
        logging.error(f"Error sending JSON: {str(e)}")
        logging.error(f"Problematic data: {str(data)[:200]}")

def receive_message():
    """Read a message from stdin (Claude)"""
    try:
        line = sys.stdin.readline()
        if not line:
            return None  # EOF
        line = line.strip()
        if not line:
            return None  # Empty line
        
        logging.debug(f"Received message: {line[:100]}...")
        return line
    except Exception as e:
        logging.error(f"Error reading message: {str(e)}")
        return None

def send_to_rhino(message):
    """Send a command to Rhino socket server and get the response"""
    try:
        logging.info(f"Connecting to Rhino on localhost:{RHINO_PORT}")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)  # 10 second timeout
        sock.connect(("localhost", RHINO_PORT))
        
        # Send message
        if isinstance(message, str):
            message_bytes = message.encode('utf-8')
        else:
            message_bytes = json.dumps(message).encode('utf-8')
            
        sock.sendall(message_bytes)
        
        # Read response
        buffer_size = 16384
        response_bytes = sock.recv(buffer_size)
        response = response_bytes.decode('utf-8')
        
        sock.close()
        logging.info(f"Received response from Rhino: {response[:100]}...")
        return response
    except Exception as e:
        logging.error(f"Error communicating with Rhino: {str(e)}")
        return json.dumps({"error": f"Error communicating with Rhino: {str(e)}"})

def handle_initialize():
    """Handle the initialize request and return server capabilities"""
    logging.info("Processing initialize request")
    
    # Return hard-coded initialization response with tools
    response = {
        "jsonrpc": "2.0",
        "id": 0,
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
    
    return response

def handle_tool_call(request):
    """Handle a tool call request and forward to Rhino"""
    tool_name = request["params"]["name"]
    parameters = request["params"]["parameters"]
    request_id = request.get("id", 0)
    
    logging.info(f"Executing tool: {tool_name}")
    
    # Map tool name to command type
    command_type = ""
    if tool_name.startswith("geometry_tools."):
        command_type = tool_name.replace("geometry_tools.", "")
    elif tool_name.startswith("scene_tools."):
        command_type = tool_name.replace("scene_tools.", "")
    
    # Create command object
    command = {
        "Type": command_type,
        "Params": parameters
    }
    
    # Send to Rhino and get result
    result = send_to_rhino(command)
    
    # Try to parse result as JSON
    try:
        result_obj = json.loads(result)
    except:
        result_obj = {"result": result}
    
    # Return response
    response = {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "result": result_obj
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
    """Process an incoming message and generate a response"""
    try:
        request = json.loads(message)
        method = request.get("method", "")
        
        if method == "initialize":
            return handle_initialize()
        elif method == "tools/call":
            return handle_tool_call(request)
        elif method == "shutdown":
            return handle_shutdown(request)
        else:
            logging.warning(f"Unknown method: {method}")
            return {
                "jsonrpc": "2.0",
                "id": request.get("id", 0),
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            }
    except Exception as e:
        logging.error(f"Error processing message: {str(e)}")
        return {
            "jsonrpc": "2.0",
            "id": 0,
            "error": {
                "code": -32603,
                "message": f"Internal error: {str(e)}"
            }
        }

def main_loop():
    """Main server loop to process messages"""
    logging.info("Starting MCP server main loop")
    
    while not EXIT_FLAG:
        try:
            # Read message from stdin
            message = receive_message()
            
            # Handle EOF or empty line
            if message is None:
                # This is a normal client disconnect
                logging.info("Client disconnected (input stream EOF)")
                time.sleep(1)  # Prevent CPU spinning
                continue
            
            # Process message
            response = process_message(message)
            
            # Send response
            send_json_response(response)
            
        except Exception as e:
            logging.error(f"Error in main loop: {str(e)}")
            time.sleep(0.1)  # Prevent tight error loops
    
    logging.info("Main loop exited")

def signal_handler(sig, frame):
    """Handle termination signals"""
    logging.info(f"Received signal {sig}, shutting down...")
    global EXIT_FLAG
    EXIT_FLAG = True

if __name__ == "__main__":
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logging.info("=== Standalone MCP Server Starting ===")
    logging.info(f"Process ID: {os.getpid()}")
    logging.info(f"Python version: {sys.version}")
    logging.info(f"Working directory: {os.getcwd()}")
    logging.info(f"Log file: {log_file}")
    
    try:
        # Start the main processing loop
        main_loop()
    except KeyboardInterrupt:
        logging.info("Keyboard interrupt received, shutting down...")
    except Exception as e:
        logging.error(f"Fatal error: {str(e)}")
    finally:
        logging.info("=== Server Shutdown Complete ===") 