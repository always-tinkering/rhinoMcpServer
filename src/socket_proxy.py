#!/usr/bin/env python3
"""
Socket Proxy for MCP Server
This script acts as a proxy between Claude Desktop and our daemon server.
It forwards stdin to the daemon server and stdout back to Claude Desktop.
"""

import json
import os
import socket
import sys
import time
import logging
import signal
import traceback
import subprocess
import threading

# Configure logging - to file only, NOT stdout or stderr
log_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(log_dir)
log_file = os.path.join(root_dir, "logs", "socket_proxy.log")
os.makedirs(os.path.dirname(log_file), exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_file)
    ]
)

# Global variables
SERVER_PORT = 8765  # Must match port in daemon_mcp_server.py
EXIT_FLAG = False
INITIALIZED = False  # Flag to track if we've been initialized

def ensure_daemon_running():
    """Make sure the daemon server is running"""
    daemon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "daemon_mcp_server.py")
    pid_file = os.path.join(root_dir, "logs", "daemon_server.pid")
    
    # Check if PID file exists and process is running
    if os.path.exists(pid_file):
        try:
            with open(pid_file, 'r') as f:
                pid = int(f.read().strip())
            
            # Try to send signal 0 to check if process exists
            os.kill(pid, 0)
            logging.info(f"Daemon server already running with PID {pid}")
            return True
        except (OSError, ValueError):
            logging.info("Daemon server PID file exists but process is not running")
            # Remove stale PID file
            try:
                os.remove(pid_file)
            except:
                pass
    
    # Start the daemon server
    logging.info("Starting daemon server...")
    try:
        # Make daemon script executable
        os.chmod(daemon_path, 0o755)
        
        # Start the daemon in the background
        subprocess.Popen(
            [daemon_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        
        # Wait for the daemon to start
        for _ in range(10):
            if os.path.exists(pid_file):
                logging.info("Daemon server started successfully")
                return True
            time.sleep(0.5)
        
        logging.error("Timeout waiting for daemon server to start")
        return False
    except Exception as e:
        logging.error(f"Error starting daemon server: {e}")
        return False

def connect_to_daemon():
    """Connect to the daemon server"""
    for i in range(5):  # Try 5 times with exponential backoff
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(('localhost', SERVER_PORT))
            logging.info("Connected to daemon server")
            return sock
        except (socket.error, ConnectionRefusedError) as e:
            logging.warning(f"Connection attempt {i+1} failed: {e}")
            time.sleep(2 ** i)  # Exponential backoff
    
    logging.error("Failed to connect to daemon server after multiple attempts")
    return None

def forward_stdin_to_socket(sock):
    """Forward stdin to socket"""
    global INITIALIZED
    logging.info("Starting stdin forwarding thread")
    
    try:
        while not EXIT_FLAG:
            try:
                # Read a line from stdin
                line = sys.stdin.readline()
                if not line:
                    if INITIALIZED:
                        logging.info("Stdin closed but initialized - staying alive")
                        # Sleep longer to reduce log spam
                        time.sleep(30)
                        continue
                    else:
                        logging.info("Stdin closed")
                        break
                
                # Check if this is an initialize message
                try:
                    message = json.loads(line)
                    if message.get("method") == "initialize":
                        logging.info("Detected initialize message - will ignore termination signals")
                        INITIALIZED = True
                except:
                    pass
                
                # Forward to socket with newline termination
                try:
                    sock.sendall(line.encode('utf-8'))
                    logging.debug(f"Forwarded to socket: {line.strip()}")
                except socket.error as e:
                    logging.error(f"Socket error when forwarding stdin: {e}")
                    if INITIALIZED:
                        # If we're initialized, try to reconnect
                        logging.info("Trying to reconnect after socket error...")
                        try:
                            sock.close()
                        except:
                            pass
                        
                        new_sock = connect_to_daemon()
                        if new_sock:
                            sock = new_sock
                            # Re-send the original message that failed
                            sock.sendall(line.encode('utf-8'))
                            logging.info("Reconnected and resent message")
                        else:
                            logging.error("Failed to reconnect after socket error")
                            if not INITIALIZED:
                                break
                    else:
                        break
            except Exception as e:
                logging.error(f"Error forwarding stdin: {e}")
                if INITIALIZED:
                    # If we're initialized, just sleep and continue
                    time.sleep(5)
                    continue
                else:
                    break
    except Exception as e:
        logging.error(f"Fatal error in stdin forwarding: {e}")
    finally:
        logging.info("Stdin forwarding thread exiting")

def forward_socket_to_stdout(sock):
    """Forward socket responses to stdout"""
    global INITIALIZED  # Move global declaration to beginning of function
    logging.info("Starting socket forwarding thread")
    
    buffer = b""
    try:
        while not EXIT_FLAG:
            try:
                # Read data from socket
                data = sock.recv(4096)
                if not data:
                    logging.info("Socket closed by server")
                    if INITIALIZED:
                        # Try to reconnect
                        logging.info("Trying to reconnect to daemon server...")
                        try:
                            sock.close()
                        except:
                            pass
                            
                        new_sock = connect_to_daemon()
                        if new_sock:
                            sock = new_sock
                            sock.settimeout(2.0)  # Make sure timeout is set on new socket
                            logging.info("Reconnected to daemon server")
                            continue
                        else:
                            # If reconnection fails but we're initialized, just sleep and retry
                            logging.info("Reconnection failed, but we're initialized - will retry later")
                            time.sleep(5)
                            continue
                    break
                
                # Add to buffer
                buffer += data
                
                # Process complete messages (assuming each message ends with newline)
                while b'\n' in buffer:
                    line, buffer = buffer.split(b'\n', 1)
                    if line:
                        # Forward to stdout
                        line_str = line.decode('utf-8')
                        
                        # Check if this is an initialization response before forwarding
                        try:
                            response = json.loads(line_str)
                            if isinstance(response, dict) and "jsonrpc" in response and "result" in response:
                                if "serverInfo" in response.get("result", {}):
                                    logging.info("Detected initialization response - setting INITIALIZED flag")
                                    INITIALIZED = True
                        except:
                            pass
                            
                        # Always forward to stdout
                        print(line_str, flush=True)
                        logging.debug(f"Forwarded to stdout: {line_str}")
            except socket.timeout:
                # Just a timeout, not an error
                continue
            except Exception as e:
                logging.error(f"Error reading from socket: {e}")
                if INITIALIZED:
                    # If we're initialized, try to reconnect
                    try:
                        sock.close()
                    except:
                        pass
                    
                    time.sleep(1)
                    new_sock = connect_to_daemon()
                    if new_sock:
                        sock = new_sock
                        sock.settimeout(2.0)  # Make sure timeout is set on new socket
                        logging.info("Reconnected to daemon server after error")
                        continue
                    else:
                        # If reconnection fails but we're initialized, just sleep and retry
                        logging.info("Reconnection failed after error, but we're initialized - will retry later")
                        time.sleep(5)
                        continue
                break
    except Exception as e:
        logging.error(f"Fatal error in socket forwarding: {e}")
    finally:
        logging.info("Socket forwarding thread exiting")
        # If we're initialized, automatically restart the thread
        if INITIALIZED and not EXIT_FLAG:
            logging.info("Socket thread exited but we're initialized - restarting socket thread")
            time.sleep(1)  # Brief pause before reconnecting
            new_sock = connect_to_daemon()
            if new_sock:
                new_sock.settimeout(2.0)  # Make sure timeout is set on new socket
                new_thread = threading.Thread(target=forward_socket_to_stdout, args=(new_sock,))
                new_thread.daemon = True
                new_thread.start()

def signal_handler(sig, frame):
    """Handle termination signals"""
    global EXIT_FLAG
    
    logging.info(f"Received signal {sig}")
    
    # If initialized, ignore termination signals
    if INITIALIZED:
        logging.info(f"Ignoring signal {sig} after initialization")
        return
    
    # Otherwise, exit normally
    logging.info(f"Exiting due to signal {sig}")
    EXIT_FLAG = True

def main():
    """Main function"""
    global EXIT_FLAG
    
    # Register signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Create a PID file to indicate we're running
    pid_file = os.path.join(root_dir, "logs", "socket_proxy.pid")
    with open(pid_file, "w") as f:
        f.write(str(os.getpid()))
    
    logging.info("=== Socket Proxy Starting ===")
    logging.info(f"Process ID: {os.getpid()}")
    
    try:
        # Make sure the daemon is running
        if not ensure_daemon_running():
            logging.error("Failed to start daemon server")
            return 1
        
        # Connect to the daemon
        sock = connect_to_daemon()
        if not sock:
            logging.error("Failed to connect to daemon server")
            return 1
        
        # Set a timeout for the socket to prevent blocking indefinitely
        sock.settimeout(2.0)
        
        # Start forwarding threads
        stdin_thread = threading.Thread(target=forward_stdin_to_socket, args=(sock,))
        stdin_thread.daemon = True
        stdin_thread.start()
        
        socket_thread = threading.Thread(target=forward_socket_to_stdout, args=(sock,))
        socket_thread.daemon = True
        socket_thread.start()
        
        # Stay alive forever once initialized
        while not EXIT_FLAG:
            if not stdin_thread.is_alive() and not socket_thread.is_alive():
                if INITIALIZED:
                    logging.info("Both threads exited but we're initialized - restarting threads")
                    # Create a new socket and restart threads
                    new_sock = connect_to_daemon()
                    if new_sock:
                        sock = new_sock
                        stdin_thread = threading.Thread(target=forward_stdin_to_socket, args=(sock,))
                        stdin_thread.daemon = True
                        stdin_thread.start()
                        
                        socket_thread = threading.Thread(target=forward_socket_to_stdout, args=(sock,))
                        socket_thread.daemon = True
                        socket_thread.start()
                    else:
                        # If reconnection fails, sleep and retry
                        time.sleep(10)
                else:
                    logging.info("Both threads exited and not initialized - exiting")
                    break
            time.sleep(0.1)
    except KeyboardInterrupt:
        logging.info("Keyboard interrupt received")
    except Exception as e:
        logging.error(f"Unexpected error in main thread: {e}")
        traceback.print_exc(file=logging.FileHandler(log_file))
    finally:
        EXIT_FLAG = True
        logging.info("Shutting down...")
        try:
            # Only remove PID file if not initialized
            if not INITIALIZED and os.path.exists(pid_file):
                os.remove(pid_file)
        except:
            pass
    
    # If we're initialized, we'll stay alive forever
    if INITIALIZED:
        logging.info("Staying alive after initialization")
        # Reset EXIT_FLAG since we want to continue running
        EXIT_FLAG = False
        
        # Enter a loop that attempts to reconnect to the daemon periodically
        while True:
            try:
                if not os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), "daemon_server.pid")):
                    logging.info("Daemon server PID file not found - attempting to restart daemon")
                    ensure_daemon_running()
                
                # Check if we need to reconnect and restart threads
                if not stdin_thread.is_alive() or not socket_thread.is_alive():
                    logging.info("One or more threads not running - attempting to restart")
                    new_sock = connect_to_daemon()
                    if new_sock:
                        sock = new_sock
                        
                        if not stdin_thread.is_alive():
                            stdin_thread = threading.Thread(target=forward_stdin_to_socket, args=(sock,))
                            stdin_thread.daemon = True
                            stdin_thread.start()
                        
                        if not socket_thread.is_alive():
                            socket_thread = threading.Thread(target=forward_socket_to_stdout, args=(sock,))
                            socket_thread.daemon = True
                            socket_thread.start()
                
                time.sleep(10)  # Check every 10 seconds
            except Exception as e:
                logging.error(f"Error in reconnection loop: {e}")
                time.sleep(30)  # Longer sleep on error
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 