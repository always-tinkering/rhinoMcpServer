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

# Configure logging - ONLY to file and stderr, NOT stdout
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(log_dir, exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = os.path.join(log_dir, f"standalone_server_{timestamp}.log")

# Important: Only log to file and stderr, NEVER to stdout
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stderr)  # Only stderr, never stdout
    ]
)

# Global variables
SERVER_PROCESS = None
SERVER_LOCK = Lock()
RHINO_PORT = 9876
EXIT_FLAG = False
IGNORE_SIGNALS = False  # Flag to temporarily ignore signals during critical sections

# Create a PID file to track this process
pid_file = os.path.join(log_dir, "standalone_server.pid")
with open(pid_file, "w") as f:
    f.write(str(os.getpid()))

def send_json_response(data):
    """Send a JSON response to stdout (Claude)"""
    try:
        # Ensure it's valid JSON first
        if isinstance(data, str):
            json_obj = json.loads(data)  # Parse to validate
            json_str = data  # Use the original string
        else:
            json_str = json.dumps(data)  # Convert dict to string
        
        # Write directly to stdout buffer without any extra characters
        # This is critical for proper JSON parsing by Claude
        sys.stdout.buffer.write((json_str + "\n").encode('utf-8'))
        sys.stdout.buffer.flush()
        logging.debug(f"Sent JSON: {json_str[:100]}...")
    except Exception as e:
        logging.error(f"Error sending JSON: {str(e)}")
        logging.error(f"Problematic data: {str(data)[:200]}")

def receive_message():
    """Read a message from stdin (Claude)"""
    try:
        # Read raw bytes from stdin to avoid any potential encoding issues
        line = sys.stdin.buffer.readline()
        if not line:
            # This is an EOF, but we should not exit the server!
            # Claude Desktop disconnects after initialization, which is expected
            logging.info("Detected EOF on stdin - client disconnected, waiting for reconnection")
            return None  # EOF
        
        # Decode the bytes to string
        line_str = line.decode('utf-8').strip()
        if not line_str:
            return None  # Empty line
        
        logging.debug(f"Received message: {line_str[:100]}...")
        return line_str
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
    
    # Set flag to ignore signals during initialization
    global IGNORE_SIGNALS
    IGNORE_SIGNALS = True
    
    try:
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
    finally:
        # Reset signal flag
        IGNORE_SIGNALS = False

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
    
    # Create a keep-alive thread to handle client reconnections
    keepalive_thread = Thread(target=keepalive_ping, daemon=True)
    keepalive_thread.start()
    
    # Flag to track initialization status - we need to stay alive after initialization
    initialization_complete = False
    
    while not EXIT_FLAG:
        try:
            # Read message from stdin
            message = receive_message()
            
            # Handle EOF or empty line
            if message is None:
                # This is a normal client disconnect
                if initialization_complete:
                    logging.info("Client disconnected (expected behavior) - waiting for reconnection")
                else:
                    logging.info("Client disconnected before initialization completed")
                
                # Don't exit! Just wait for the next connection
                time.sleep(1)  # Prevent CPU spinning
                continue
            
            # Process message
            response = process_message(message)
            
            # Check if this was an initialization request
            if isinstance(response, dict) and "result" in response and "serverInfo" in response.get("result", {}):
                initialization_complete = True
                logging.info("Initialization completed successfully, server will remain alive for tool calls")
            
            # Send response
            send_json_response(response)
            
        except Exception as e:
            logging.error(f"Error in main loop: {str(e)}")
            time.sleep(0.1)  # Prevent tight error loops
    
    logging.info("Main loop exited")

def keepalive_ping():
    """Thread function to keep the server alive during client reconnections"""
    while not EXIT_FLAG:
        # Just write a small log message every 30 seconds to show we're alive
        logging.debug("Keepalive thread active - server is waiting for requests")
        time.sleep(30)

def signal_handler(sig, frame):
    """Handle termination signals"""
    if IGNORE_SIGNALS:
        logging.warning(f"Received signal {sig} but ignoring during critical operation")
        return
        
    logging.info(f"Received signal {sig}, shutting down...")
    global EXIT_FLAG
    EXIT_FLAG = True

def cleanup():
    """Clean up resources when exiting"""
    # Remove PID file
    try:
        if os.path.exists(pid_file):
            os.remove(pid_file)
    except Exception as e:
        logging.error(f"Error removing PID file: {str(e)}")

if __name__ == "__main__":
    # Make sure stdout is clean at startup
    sys.stdout.flush()
    
    # Set up signal handlers - but make them more resilient
    # SIGTERM (15) - termination request
    signal.signal(signal.SIGTERM, signal_handler)
    # SIGINT (2) - keyboard interrupt
    signal.signal(signal.SIGINT, signal_handler)
    # SIGHUP (1) - terminal closed
    signal.signal(signal.SIGHUP, signal_handler)
    
    # Get the current working directory
    working_dir = os.getcwd()
    
    # Log to stderr only
    logging.info("=== Standalone MCP Server Starting ===")
    logging.info(f"Process ID: {os.getpid()}")
    logging.info(f"Python version: {sys.version}")
    logging.info(f"Working directory: {working_dir}")
    logging.info(f"Log file: {log_file}")
    
    # Register the cleanup function to run at exit
    import atexit
    atexit.register(cleanup)
    
    try:
        # Update the current directory - very important!
        # Claude Desktop might start us in /, which isn't helpful
        if working_dir == "/":
            script_dir = os.path.dirname(os.path.abspath(__file__))
            os.chdir(script_dir)
            logging.info(f"Changed working directory to: {script_dir}")
        
        # Start the main processing loop
        main_loop()
    except KeyboardInterrupt:
        logging.info("Keyboard interrupt received, shutting down...")
    except Exception as e:
        logging.error(f"Fatal error: {str(e)}")
    finally:
        cleanup()
        logging.info("=== Server Shutdown Complete ===") 