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
import threading
import traceback
import queue
from datetime import datetime
from threading import Thread, Lock, Event

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
SERVER_STATE = "waiting"  # States: waiting, initialized, processing
CONNECTION_EVENT = Event()  # Event to signal when a connection is made
RECONNECT_TIMEOUT = 60.0  # Wait up to 60 seconds for reconnection before checking status
MESSAGE_QUEUE = queue.Queue()  # Queue for messages between threads
NEW_MESSAGE_EVENT = Event()  # Event to signal when a new message is available

# Create a PID file to track this process
pid_file = os.path.join(log_dir, "standalone_server.pid")
with open(pid_file, "w") as f:
    f.write(str(os.getpid()))

def send_json_response(data):
    """Send a JSON response to stdout (Claude)"""
    try:
        # Ensure we're sending a valid JSON object
        if isinstance(data, str):
            try:
                # Parse to validate and re-serialize to ensure clean JSON
                json_obj = json.loads(data)
                json_str = json.dumps(json_obj)
            except json.JSONDecodeError as e:
                logging.error(f"Invalid JSON string provided: {str(e)}")
                logging.error(f"Problematic data: {str(data)[:200]}")
                return
        else:
            # Convert dict to a clean JSON string
            json_str = json.dumps(data)
        
        # Ensure stdout is clean before writing
        sys.stdout.flush()
        
        # Write as bytes with just the JSON string and a newline, nothing else
        sys.stdout.buffer.write(json_str.encode('utf-8'))
        sys.stdout.buffer.write(b'\n')
        sys.stdout.buffer.flush()
        
        logging.debug(f"Sent JSON: {json_str[:100]}...")
    except Exception as e:
        logging.error(f"Error sending JSON: {str(e)}")
        logging.error(f"Stack trace: {traceback.format_exc()}")
        logging.error(f"Problematic data: {str(data)[:200]}")

def receive_message(timeout=None, from_queue=False):
    """
    Read a message from stdin (Claude) with optional timeout
    
    Args:
        timeout: If provided, wait up to this many seconds for input before returning None
        from_queue: If True, read from the message queue instead of stdin
    
    Returns:
        The message string or None if EOF or timeout
    """
    if from_queue:
        # Try to get a message from the queue
        try:
            if timeout is not None:
                # Use timeout if provided
                try:
                    return MESSAGE_QUEUE.get(block=True, timeout=timeout)
                except queue.Empty:
                    return None
            else:
                # No timeout, will block indefinitely
                return MESSAGE_QUEUE.get(block=True)
        except Exception as e:
            logging.error(f"Error reading from message queue: {str(e)}")
            return None
    
    # Standard read from stdin
    try:
        # If timeout is requested, use a separate thread for reading
        if timeout is not None:
            result = [None]
            
            def read_input():
                try:
                    line = sys.stdin.buffer.readline()
                    if not line:
                        result[0] = None  # EOF
                        logging.warning("EOF detected on stdin - client disconnected")
                        return
                    
                    line_str = line.decode('utf-8').strip()
                    if not line_str:
                        result[0] = None  # Empty line
                        logging.warning("Empty line received on stdin")
                    else:
                        result[0] = line_str
                        # Log the full message content for debugging
                        if '"method":"initialize"' in line_str:
                            logging.info(f"RECEIVED INITIALIZE MESSAGE: {line_str}")
                        else:
                            logging.debug(f"Received message: {line_str[:100]}...")
                except Exception as e:
                    logging.error(f"Error in read_input thread: {str(e)}")
                    logging.error(f"Stack trace: {traceback.format_exc()}")
                    result[0] = None
                finally:
                    CONNECTION_EVENT.set()  # Signal that reading is done
            
            # Create and start the thread
            read_thread = Thread(target=read_input, daemon=True)
            CONNECTION_EVENT.clear()
            read_thread.start()
            
            # Wait for the thread to complete or timeout
            CONNECTION_EVENT.wait(timeout)
            
            if result[0] is None and not CONNECTION_EVENT.is_set():
                logging.debug(f"Receive timeout after {timeout} seconds")
            
            return result[0]
        
        # Standard synchronous read if no timeout
        line = sys.stdin.buffer.readline()
        if not line:
            logging.info("Detected EOF on stdin - client disconnected, waiting for reconnection")
            return None  # EOF
        
        # Decode the bytes to string
        line_str = line.decode('utf-8').strip()
        if not line_str:
            logging.warning("Empty line received on stdin")
            return None  # Empty line
        
        # Log the full message for important messages
        if '"method":"initialize"' in line_str:
            logging.info(f"RECEIVED INITIALIZE MESSAGE: {line_str}")
        else:
            logging.debug(f"Received message: {line_str[:100]}...")
            
        return line_str
    except Exception as e:
        logging.error(f"Error reading message: {str(e)}")
        logging.error(f"Stack trace: {traceback.format_exc()}")
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

def handle_initialize(request=None):
    """Handle the initialize request and return server capabilities"""
    logging.info("Processing initialize request")
    
    # Get request ID from the client (default to 0 if not provided)
    request_id = 0
    if request and isinstance(request, dict):
        request_id = request.get("id", 0)
        logging.info(f"Using request ID from client: {request_id}")
    
    # Set flag to ignore signals during initialization
    global IGNORE_SIGNALS, SERVER_STATE
    IGNORE_SIGNALS = True
    
    try:
        # Log detailed info about the request
        if request:
            logging.info(f"Initialize request details: {json.dumps(request)[:200]}...")
        
        # Return hard-coded initialization response with tools
        response = {
            "jsonrpc": "2.0",
            "id": request_id,  # Use the client's request ID
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
        
        # Log the response before sending
        logging.info(f"Response prepared: {json.dumps(response)[:200]}...")
        
        # Mark server as initialized after successful response
        SERVER_STATE = "initialized"
        logging.info("Server initialized successfully - will stay alive for reconnections")
        
        # Convert all Python booleans to JSON booleans
        json_str = json.dumps(response)
        response = json.loads(json_str)
        
        return response
    finally:
        # Reset signal flag
        IGNORE_SIGNALS = False

def handle_tool_call(request):
    """Handle a tool call request and forward to Rhino"""
    global SERVER_STATE
    SERVER_STATE = "processing"
    
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
    
    SERVER_STATE = "initialized"  # Return to initialized state after processing
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
        
        logging.info(f"Processing method: {method} with request ID: {request.get('id', 'unknown')}")
        
        if method == "initialize":
            return handle_initialize(request)  # Pass the entire request to handle_initialize
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
        logging.error(f"Stack trace: {traceback.format_exc()}")
        return {
            "jsonrpc": "2.0",
            "id": 0,
            "error": {
                "code": -32603,
                "message": f"Internal error: {str(e)}"
            }
        }

def connection_monitor():
    """
    Monitor thread that prevents the server from exiting when clients disconnect.
    Checks server health and performs periodic actions.
    """
    global EXIT_FLAG, SERVER_STATE
    
    logging.info("Connection monitor started")
    
    while not EXIT_FLAG:
        try:
            # Log server state periodically
            logging.debug(f"Server state: {SERVER_STATE}")
            
            # Check if Rhino is still accessible
            if SERVER_STATE == "initialized":
                # Perform any needed maintenance here
                pass
                
            # Sleep to prevent tight loop
            time.sleep(5)
        except Exception as e:
            logging.error(f"Error in connection monitor: {str(e)}")
            logging.error(f"Stack trace: {traceback.format_exc()}")
            time.sleep(10)  # Longer sleep on error
    
    logging.info("Connection monitor exiting")

def persist_stdin():
    """
    Keeps stdin open even when there's no active client connection.
    This is crucial for the MCP protocol. This thread reads messages from stdin
    and puts them into a queue for the main thread to process.
    """
    global EXIT_FLAG
    
    logging.info("Stdin persistence thread started")
    
    while not EXIT_FLAG:
        try:
            # Try to read any inputs that might be available
            # Unlike before, we don't use a timeout here because we want to block
            # waiting for input
            line = sys.stdin.buffer.readline()
            if not line:
                logging.warning("EOF detected on stdin in persistence thread - client disconnected")
                time.sleep(0.5)  # Short sleep to prevent tight loops on EOF
                continue
                
            # Decode the bytes to string
            line_str = line.decode('utf-8').strip()
            if not line_str:
                logging.warning("Empty line received on stdin in persistence thread")
                continue
                
            # Log the message
            if '"method":"initialize"' in line_str:
                logging.info(f"STDIN THREAD RECEIVED INITIALIZE MESSAGE: {line_str}")
            else:
                logging.debug(f"STDIN thread received message: {line_str[:100]}...")
                
            # Put the message in the queue for the main thread to process
            MESSAGE_QUEUE.put(line_str)
            logging.info("Message added to processing queue")
            NEW_MESSAGE_EVENT.set()  # Signal that a new message is available
            
        except Exception as e:
            logging.error(f"Error in persist_stdin: {str(e)}")
            logging.error(f"Stack trace: {traceback.format_exc()}")
            time.sleep(1)
    
    logging.info("Stdin persistence thread exiting")

def keepalive_ping():
    """Thread function to keep the server alive during client reconnections"""
    global EXIT_FLAG
    
    logging.info("Keepalive thread started")
    
    while not EXIT_FLAG:
        try:
            # Just write a message to logs every 30 seconds to show we're alive
            logging.debug("Keepalive thread active - server is waiting for requests")
            
            # Sleep to prevent tight loop
            time.sleep(30)
        except Exception as e:
            logging.error(f"Error in keepalive thread: {str(e)}")
            time.sleep(10)  # Longer sleep on error
    
    logging.info("Keepalive thread exiting")

def main_loop():
    """Main server loop to process messages"""
    global SERVER_STATE
    
    logging.info("Starting MCP server main loop")
    logging.info("WAITING FOR INITIALIZE MESSAGE FROM CLAUDE...")
    
    # Ensure stdout is completely clean at startup
    sys.stdout.flush()
    sys.stdout.buffer.flush()
    
    # Create connection monitoring thread
    monitor_thread = Thread(target=connection_monitor, daemon=True)
    monitor_thread.start()
    
    # Create stdin persistence thread 
    stdin_thread = Thread(target=persist_stdin, daemon=True)
    stdin_thread.start()
    
    # Create a keep-alive thread to handle client reconnections
    keepalive_thread = Thread(target=keepalive_ping, daemon=True)
    keepalive_thread.start()
    
    # Flag to track whether we've printed the reconnection message
    reconnection_message_printed = False
    
    while not EXIT_FLAG:
        try:
            # If we're in initialized state, let's notify about waiting for reconnection
            if SERVER_STATE == "initialized" and not reconnection_message_printed:
                logging.info("===== IMPORTANT: Server is now in initialized state =====")
                logging.info("The server will wait for Claude to reconnect. This is NORMAL behavior.")
                logging.info("DO NOT restart the server manually when Claude disconnects after initialization.")
                reconnection_message_printed = True
            
            logging.debug(f"Main loop waiting for message (state: {SERVER_STATE})")
            
            # First, check if there's a message in the queue
            # We'll wait for a very short time to avoid tight loops
            message = None
            try:
                message = MESSAGE_QUEUE.get(block=False)
                logging.info(f"Retrieved message from queue: {message[:50]}...")
            except queue.Empty:
                # If no message in queue, wait with a short timeout
                NEW_MESSAGE_EVENT.wait(0.1)
                NEW_MESSAGE_EVENT.clear()
                
                # If still nothing, fall back to normal stdin reading with a timeout
                if MESSAGE_QUEUE.empty():
                    # Read message from stdin with a timeout
                    logging.debug("No message in queue, checking stdin...")
                    message = None  # Don't try to read stdin, the persistence thread does that
                else:
                    continue  # Loop back and try the queue again
            
            # If no message, just check if we need to exit and continue
            if message is None:
                if EXIT_FLAG:
                    break
                    
                # Reset reconnection message if we get a new connection after waiting
                if reconnection_message_printed and SERVER_STATE == "waiting":
                    reconnection_message_printed = False
                    
                continue
            
            # Log that we received a message  
            logging.info(f"Processing message: {message[:50]}...")
                
            # Process message and get response
            try:
                response = process_message(message)
                
                # Validate the response is a proper dictionary before sending
                if not isinstance(response, (dict, str)):
                    logging.error(f"Invalid response type: {type(response)}")
                    continue
                    
                # Send response
                logging.info("Sending response to Claude...")
                send_json_response(response)
                logging.info("Response sent successfully")
            except Exception as e:
                logging.error(f"Error processing or sending message: {str(e)}")
                logging.error(f"Stack trace: {traceback.format_exc()}")
                # Don't crash the server on individual message processing errors
            
            # Small delay to prevent tight loops
            time.sleep(0.01)
            
        except Exception as e:
            logging.error(f"Error in main loop: {str(e)}")
            logging.error(f"Stack trace: {traceback.format_exc()}")
            time.sleep(1)  # Prevent tight error loops
    
    logging.info("Main loop exited")

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
        logging.error(f"Stack trace: {traceback.format_exc()}")
    finally:
        cleanup()
        logging.info("=== Server Shutdown Complete ===") 