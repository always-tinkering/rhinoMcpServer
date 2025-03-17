#!/usr/bin/env python3
"""
Daemon MCP Server for Rhino
This script implements a socket-based MCP server that runs in the background
and allows multiple connections from Claude Desktop.
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
import socketserver

# Configure logging - log to both stderr and a file
log_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(log_dir)
log_file = os.path.join(root_dir, "logs", "daemon_mcp_server.log")
os.makedirs(os.path.dirname(log_file), exist_ok=True)

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
SOCKET_PORT = 8765  # Port for the socket server

# Create a PID file to track this process
pid_file = os.path.join(root_dir, "logs", "daemon_server.pid")
with open(pid_file, "w") as f:
    f.write(str(os.getpid()))

# Tools configuration - shared among all connections
SERVER_CAPABILITIES = {
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

class MCPRequestHandler(socketserver.BaseRequestHandler):
    """
    Handler for MCP requests over a TCP socket
    """
    def handle(self):
        """Handle requests from a client"""
        self.client_connected = True
        self.local_state = "waiting"
        logging.info(f"Client connected from {self.client_address}")
        
        try:
            buffer = b""
            while not EXIT_FLAG and self.client_connected:
                try:
                    # Read data from socket
                    data = self.request.recv(4096)
                    if not data:
                        # Client disconnected
                        logging.info(f"Client disconnected: {self.client_address}")
                        self.client_connected = False
                        break
                    
                    # Add received data to buffer
                    buffer += data
                    
                    # Process complete messages (assuming each message ends with newline)
                    while b'\n' in buffer:
                        line, buffer = buffer.split(b'\n', 1)
                        if line:
                            line_str = line.decode('utf-8')
                            self.process_message(line_str)
                except json.JSONDecodeError as e:
                    logging.error(f"Invalid JSON: {e}")
                    continue
                except Exception as e:
                    logging.error(f"Error handling client: {e}")
                    traceback.print_exc()
                    # Don't break here - try to continue handling client
                    time.sleep(0.1)
                    continue
        finally:
            logging.info(f"Client handler exiting: {self.client_address}")
    
    def process_message(self, message_str):
        """Process a message from the client"""
        try:
            message = json.loads(message_str)
            method = message.get("method", "")
            logging.info(f"Processing message: {method}")
            
            if method == "initialize":
                self.handle_initialize(message)
            elif method == "tools/call":
                self.handle_tool_call(message)
            elif method == "shutdown":
                self.handle_shutdown(message)
            elif method == "notifications/cancelled":
                logging.info("Received cancellation notification")
            else:
                logging.warning(f"Unknown method: {method}")
                # Send error response for unknown methods
                response = {
                    "jsonrpc": "2.0",
                    "id": message.get("id", 0),
                    "error": {
                        "code": -32601,
                        "message": f"Method '{method}' not found"
                    }
                }
                self.send_response(response)
        except Exception as e:
            logging.error(f"Error processing message: {e}")
            traceback.print_exc()
            # Try to send error response
            try:
                response = {
                    "jsonrpc": "2.0",
                    "id": message.get("id", 0) if isinstance(message, dict) else 0,
                    "error": {
                        "code": -32603,
                        "message": f"Internal error: {str(e)}"
                    }
                }
                self.send_response(response)
            except:
                pass
    
    def handle_initialize(self, request):
        """Handle initialize request"""
        global SERVER_STATE
        request_id = request.get("id", 0)
        
        # Set the global server state to initialized
        SERVER_STATE = "initialized"
        self.local_state = "initialized"
        logging.info("Server initialized successfully")
        
        # Create response
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": SERVER_CAPABILITIES
        }
        
        # Send response
        self.send_response(response)
        
        # Keep the connection open - don't close after initialization
        logging.info("Initialization complete, keeping connection open for further requests")
    
    def handle_tool_call(self, request):
        """Handle tool call request"""
        tool_name = request["params"]["name"]
        parameters = request["params"]["parameters"]
        request_id = request.get("id", 0)
        
        logging.info(f"Executing tool: {tool_name}")
        
        # Return dummy success response
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "result": {"success": True, "message": f"Executed {tool_name} with parameters {parameters}"}
            }
        }
        
        self.send_response(response)
    
    def handle_shutdown(self, request):
        """Handle shutdown request"""
        request_id = request.get("id", 0)
        logging.info("Shutdown requested by client")
        
        # Only shut down this client connection, not the entire server
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {"success": True}
        }
        
        self.send_response(response)
        self.client_connected = False
    
    def send_response(self, data):
        """Send JSON response to the client"""
        try:
            # Serialize to JSON and add newline
            json_str = json.dumps(data) + "\n"
            
            # Send as bytes
            self.request.sendall(json_str.encode('utf-8'))
            logging.debug(f"Sent response: {json_str[:100]}...")
        except Exception as e:
            logging.error(f"Error sending response: {e}")
            traceback.print_exc()
            # Don't close the connection on send error
            logging.info("Continuing despite send error")

class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    """Threaded TCP Server that allows for multiple simultaneous connections"""
    daemon_threads = True
    allow_reuse_address = True

def signal_handler(sig, frame):
    """Handle termination signals"""
    global EXIT_FLAG
    
    logging.info(f"Received signal {sig}")
    
    # If server is in critical section, delay for a bit
    if SERVER_STATE != "waiting":
        logging.info("Server is busy, delaying shutdown...")
        time.sleep(1)
    
    # Set exit flag to trigger graceful shutdown
    EXIT_FLAG = True

def cleanup():
    """Clean up resources when exiting"""
    try:
        if os.path.exists(pid_file):
            os.remove(pid_file)
            logging.info("Removed PID file")
    except Exception as e:
        logging.error(f"Error in cleanup: {e}")

def main():
    """Main function"""
    global EXIT_FLAG
    
    # Register signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Register cleanup handler
    import atexit
    atexit.register(cleanup)
    
    logging.info("=== Daemon MCP Server Starting ===")
    logging.info(f"Process ID: {os.getpid()}")
    logging.info(f"Listening on port {SOCKET_PORT}")
    
    # Create the server
    server = ThreadedTCPServer(('localhost', SOCKET_PORT), MCPRequestHandler)
    
    # Start a thread with the server
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    
    try:
        # Keep the main thread running
        while not EXIT_FLAG:
            time.sleep(0.1)
    except KeyboardInterrupt:
        logging.info("Keyboard interrupt received")
    finally:
        logging.info("Server shutting down...")
        server.shutdown()
        cleanup()

if __name__ == "__main__":
    main() 