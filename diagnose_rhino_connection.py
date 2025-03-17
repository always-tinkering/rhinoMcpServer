#!/usr/bin/env python3
"""
Diagnostic script for testing connection to Rhino
"""

import socket
import json
import sys
import time
import os
import logging
from datetime import datetime
import traceback

# Configure diagnostic logging to use the same structure as the server
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
diagnostic_log_dir = os.path.join(log_dir, "diagnostics")
os.makedirs(diagnostic_log_dir, exist_ok=True)

# Create timestamped log file
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
diagnostic_log_file = os.path.join(diagnostic_log_dir, f"rhino_diagnostic_{timestamp}.log")

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] [%(levelname)s] [diagnostic] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(diagnostic_log_file)
    ]
)

logger = logging.getLogger()
print(f"Logging diagnostic results to: {diagnostic_log_file}")

def send_command(command_type, params=None):
    """Send a command to Rhino and return the response"""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    try:
        logger.info(f"Connecting to Rhino on localhost:9876...")
        s.connect(('localhost', 9876))
        logger.info("Connected successfully")
        
        command = {
            "id": f"diag_{int(time.time())}",
            "type": command_type,
            "params": params or {}
        }
        
        command_json = json.dumps(command)
        logger.info(f"Sending command: {command_json}")
        s.sendall(command_json.encode('utf-8'))
        
        # Set a timeout for receiving
        s.settimeout(10.0)
        
        # Receive the response
        buffer_size = 4096
        response_data = b""
        
        logger.info("Waiting for response...")
        while True:
            chunk = s.recv(buffer_size)
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
        
        logger.info("Raw response from Rhino:")
        logger.info(response_data.decode('utf-8'))
        
        try:
            response = json.loads(response_data.decode('utf-8'))
            logger.info("Parsed response:")
            logger.info(json.dumps(response, indent=2))
            
            # Check for errors in the response
            if "error" in response:
                error_msg = response.get("error", "Unknown error")
                logger.error(f"Error processing command: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg
                }
            
            if response.get("status") == "error":
                error_msg = response.get("message", "Unknown error")
                logger.error(f"Error status in response: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg
                }
                
            logger.info("Command executed successfully")
            return {
                "success": True,
                "result": response.get("result", response)
            }
        except Exception as e:
            logger.error(f"Error parsing response: {e}")
            logger.error(traceback.format_exc())
            return {
                "success": False,
                "error": f"Error parsing response: {e}"
            }
    
    except Exception as e:
        logger.error(f"Communication error: {e}")
        logger.error(traceback.format_exc())
        return {
            "success": False,
            "error": f"Communication error: {e}"
        }
    finally:
        s.close()

def main():
    print("\n" + "="*50)
    print("=== Rhino Connection Diagnostic Tool ===")
    print("="*50 + "\n")
    
    # Record environment info
    logger.info(f"Running diagnostic from: {os.getcwd()}")
    
    # Test basic socket connection
    print("\n--- Testing Socket Connection ---")
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5.0)
        s.connect(('localhost', 9876))
        s.close()
        print("✅ Socket connection to port 9876 successful")
        logger.info("Socket connection test: SUCCESS")
        socket_success = True
    except Exception as e:
        print(f"❌ Socket connection failed: {e}")
        logger.error(f"Socket connection test: FAILED - {e}")
        logger.error(traceback.format_exc())
        print("Make sure Rhino is running and the plugin is loaded")
        socket_success = False
        
    if not socket_success:
        print("\n❌ Cannot continue tests without socket connection")
        return False
    
    # Test basic commands
    print("\n--- Testing GET_SCENE_INFO command ---")
    scene_info_result = send_command("get_scene_info", {})
    scene_info_success = scene_info_result.get("success", False)
    
    print("\n--- Testing CREATE_BOX command ---")
    box_params = {
        "cornerX": 0,
        "cornerY": 0,
        "cornerZ": 0,
        "width": 30,
        "depth": 30,
        "height": 40,
        "color": "red"
    }
    box_result = send_command("create_box", box_params)
    box_success = box_result.get("success", False)
    
    # Print summary
    print("\n" + "="*50)
    print("=== Diagnosis Summary ===")
    print(f"Socket Connection: {'✅ Success' if socket_success else '❌ Failed'}")
    print(f"Scene Info Command: {'✅ Success' if scene_info_success else '❌ Failed'}")
    if not scene_info_success:
        print(f"  Error: {scene_info_result.get('error', 'Unknown error')}")
    
    print(f"Create Box Command: {'✅ Success' if box_success else '❌ Failed'}")
    if not box_success:
        print(f"  Error: {box_result.get('error', 'Unknown error')}")
    
    # Save recommendations to log
    if not (scene_info_success and box_success):
        print("\nRecommended Action:")
        logger.info("DIAGNOSTIC FAILED - Recommendations:")
        recommendations = [
            "1. Close and restart Rhino completely",
            "2. Kill any running socket server processes with: pkill -f \"RhinoMcpServer.dll\"",
            "3. Make sure the RhinoMcpPlugin is loaded (use _PlugInManager command in Rhino)",
            "4. Restart the MCP server with ./run-combined-server.sh",
            "5. Run this diagnostic tool again"
        ]
        
        for rec in recommendations:
            print(rec)
            logger.info(f"RECOMMENDATION: {rec}")
        
        # Add technical details
        print("\nTechnical Details:")
        if "Object reference not set to an instance of an object" in str(scene_info_result) or "Object reference not set to an instance of an object" in str(box_result):
            print("- The null reference error suggests the Rhino plugin is not properly initialized")
            print("- This could be due to the Rhino document not being initialized")
            print("- Or there may be multiple socket server instances causing conflicts")
            logger.info("TECHNICAL: Null reference error detected - plugin initialization problem likely")
    else:
        print("\n✅ All tests passed! The Rhino connection is working properly.")
        logger.info("DIAGNOSTIC PASSED - All tests successful")

    # Record where logs are stored
    print(f"\nDetailed diagnostic log saved to: {diagnostic_log_file}")
    
    return scene_info_success and box_success

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Unhandled exception in diagnostic tool: {e}")
        logger.error(traceback.format_exc())
        print(f"\n❌ Error running diagnostic: {e}")
        sys.exit(1) 