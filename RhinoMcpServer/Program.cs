using System;
using System.Collections.Generic;
using System.IO;
using System.Net.Sockets;
using System.Text;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;

namespace RhinoMcpServer
{
    class Program
    {
        private const int PORT = 9876;  // Same port as in the RhinoSocketServer
        private static ManualResetEvent _exitEvent = new ManualResetEvent(false);
        
        static async Task Main(string[] args)
        {
            // Redirect Console.Out to Console.Error to ensure ALL output goes to stderr
            // This is critical for MCP protocol - any stdout output will break JSON parsing
            Console.SetOut(Console.Error);
            
            try
            {
                // Use Console.Error for all logging to avoid interfering with the MCP protocol
                Console.Error.WriteLine("RhinoMcpServer: Starting...");
                
                AppDomain.CurrentDomain.ProcessExit += (s, e) => 
                {
                    Console.Error.WriteLine("Process exit event triggered, shutting down...");
                    _exitEvent.Set();
                };
                
                AppDomain.CurrentDomain.UnhandledException += (s, e) =>
                {
                    Console.Error.WriteLine($"CRITICAL: Unhandled exception: {e.ExceptionObject}");
                    _exitEvent.Set();
                };
                
                // Initialize MCP protocol handlers
                var server = new McpServer();
                
                // Start the server in the background
                _ = Task.Run(async () => 
                {
                    try 
                    {
                        await server.StartAsync();
                    } 
                    catch (Exception ex)
                    {
                        Console.Error.WriteLine($"Fatal server error: {ex.Message}");
                        Console.Error.WriteLine(ex.StackTrace);
                        _exitEvent.Set();
                    }
                });
                
                // Don't wait for a key if we're being run by Claude Desktop
                // Only show this message when run manually for debugging
                if (args.Length > 0 && args[0] == "--debug")
                {
                    Console.Error.WriteLine("RhinoMcpServer: Press any key to exit");
                    Console.ReadKey();
                    _exitEvent.Set();
                }
                else
                {
                    // Log that we're waiting for events
                    Console.Error.WriteLine("RhinoMcpServer: Running and waiting for MCP messages...");
                    
                    // Block until the exit event is set (which only happens on process exit)
                    _exitEvent.WaitOne();
                    Console.Error.WriteLine("RhinoMcpServer: Exiting gracefully");
                }
            }
            catch (Exception ex)
            {
                Console.Error.WriteLine($"FATAL ERROR in main program loop: {ex.Message}");
                Console.Error.WriteLine(ex.StackTrace);
                // Exit with error code
                Environment.Exit(1);
            }
        }
    }
    
    class McpServer
    {
        private const int PORT = 9876;
        private bool keepAlive = true;
        
        public async Task StartAsync()
        {
            // Use Console.Error for all logging to avoid interfering with the MCP protocol
            Console.Error.WriteLine("Initializing server...");
            
            try
            {
                // 1. Listen for stdin/stdout communication from Claude Desktop
                var reader = new StreamReader(Console.OpenStandardInput());
                var writer = new StreamWriter(Console.OpenStandardOutput()) { AutoFlush = true };
                
                // 2. Set up message handling
                while (keepAlive)
                {
                    try
                    {
                        var line = await reader.ReadLineAsync();
                        if (line == null)
                        {
                            Console.Error.WriteLine("Input stream closed, exiting...");
                            break;
                        }
                        
                        // Only log message to stderr, NEVER to stdout
                        Console.Error.WriteLine($"Message from client: {line}");
                        
                        var response = await ProcessMcpMessage(line);
                        
                        // ONLY the JSON response goes to stdout - nothing else!
                        await writer.WriteLineAsync(response);
                        
                        // Add a small delay to allow other operations to finish
                        await Task.Delay(50);
                    }
                    catch (Exception ex)
                    {
                        Console.Error.WriteLine($"Error processing message: {ex.Message}");
                        Console.Error.WriteLine($"Stack trace: {ex.StackTrace}");
                        
                        try
                        {
                            // Try to send an error response
                            await writer.WriteLineAsync(JsonSerializer.Serialize(new
                            {
                                jsonrpc = "2.0",
                                id = 0,
                                error = new
                                {
                                    code = -32603,
                                    message = $"Internal error: {ex.Message}"
                                }
                            }));
                        }
                        catch (Exception innerEx)
                        {
                            Console.Error.WriteLine($"Failed to send error response: {innerEx.Message}");
                        }
                        
                        // Don't break the loop for errors, keep trying to process messages
                    }
                }
            }
            catch (Exception ex)
            {
                Console.Error.WriteLine($"CRITICAL ERROR in StartAsync: {ex.Message}");
                Console.Error.WriteLine($"Stack trace: {ex.StackTrace}");
            }
            
            Console.Error.WriteLine("Server shutting down...");
        }
        
        private async Task<string> ProcessMcpMessage(string message)
        {
            try
            {
                var request = JsonSerializer.Deserialize<JsonElement>(message);
                var method = request.GetProperty("method").GetString();
                
                // Safely get ID (might be missing in some messages)
                int id = 0;
                if (request.TryGetProperty("id", out JsonElement idElement))
                {
                    id = idElement.GetInt32();
                }
                
                switch (method)
                {
                    case "initialize":
                        Console.Error.WriteLine("Server started and connected successfully");
                        
                        // Return initialization response with tools and resources
                        return JsonSerializer.Serialize(new
                        {
                            jsonrpc = "2.0",
                            id,
                            result = new
                            {
                                serverInfo = new
                                {
                                    name = "RhinoMcpServer",
                                    version = "0.1.0"
                                },
                                capabilities = new
                                {
                                    tools = new object[]
                                    {
                                        new 
                                        {
                                            name = "geometry_tools.create_sphere",
                                            description = "Creates a sphere with the specified center and radius",
                                            parameters = new object[]
                                            {
                                                new { name = "centerX", description = "X coordinate of the sphere center", required = true, schema = new { type = "number" } },
                                                new { name = "centerY", description = "Y coordinate of the sphere center", required = true, schema = new { type = "number" } },
                                                new { name = "centerZ", description = "Z coordinate of the sphere center", required = true, schema = new { type = "number" } },
                                                new { name = "radius", description = "Radius of the sphere", required = true, schema = new { type = "number" } },
                                                new { name = "color", description = "Optional color for the sphere (e.g., 'red', 'blue', etc.)", required = false, schema = new { type = "string" } }
                                            }
                                        },
                                        new 
                                        {
                                            name = "geometry_tools.create_box",
                                            description = "Creates a box with the specified dimensions",
                                            parameters = new object[]
                                            {
                                                new { name = "cornerX", description = "X coordinate of the box corner", required = true, schema = new { type = "number" } },
                                                new { name = "cornerY", description = "Y coordinate of the box corner", required = true, schema = new { type = "number" } },
                                                new { name = "cornerZ", description = "Z coordinate of the box corner", required = true, schema = new { type = "number" } },
                                                new { name = "width", description = "Width of the box (X dimension)", required = true, schema = new { type = "number" } },
                                                new { name = "depth", description = "Depth of the box (Y dimension)", required = true, schema = new { type = "number" } },
                                                new { name = "height", description = "Height of the box (Z dimension)", required = true, schema = new { type = "number" } },
                                                new { name = "color", description = "Optional color for the box (e.g., 'red', 'blue', etc.)", required = false, schema = new { type = "string" } }
                                            }
                                        },
                                        new 
                                        {
                                            name = "geometry_tools.create_cylinder",
                                            description = "Creates a cylinder with the specified base point, height, and radius",
                                            parameters = new object[]
                                            {
                                                new { name = "baseX", description = "X coordinate of the cylinder base point", required = true, schema = new { type = "number" } },
                                                new { name = "baseY", description = "Y coordinate of the cylinder base point", required = true, schema = new { type = "number" } },
                                                new { name = "baseZ", description = "Z coordinate of the cylinder base point", required = true, schema = new { type = "number" } },
                                                new { name = "height", description = "Height of the cylinder", required = true, schema = new { type = "number" } },
                                                new { name = "radius", description = "Radius of the cylinder", required = true, schema = new { type = "number" } },
                                                new { name = "color", description = "Optional color for the cylinder (e.g., 'red', 'blue', etc.)", required = false, schema = new { type = "string" } }
                                            }
                                        },
                                        new 
                                        {
                                            name = "scene_tools.get_scene_info",
                                            description = "Gets information about objects in the current scene",
                                            parameters = new object[] { }
                                        },
                                        new 
                                        {
                                            name = "scene_tools.clear_scene",
                                            description = "Clears all objects from the current scene",
                                            parameters = new object[]
                                            {
                                                new { name = "currentLayerOnly", description = "If true, only delete objects on the current layer", required = false, schema = new { type = "boolean" } }
                                            }
                                        },
                                        new 
                                        {
                                            name = "scene_tools.create_layer",
                                            description = "Creates a new layer in the Rhino document",
                                            parameters = new object[]
                                            {
                                                new { name = "name", description = "Name of the new layer", required = true, schema = new { type = "string" } },
                                                new { name = "color", description = "Optional color for the layer (e.g., 'red', 'blue', etc.)", required = false, schema = new { type = "string" } }
                                            }
                                        }
                                    }
                                }
                            }
                        });
                        
                    case "tools/call":
                        var toolName = request.GetProperty("params").GetProperty("name").GetString();
                        var parameters = request.GetProperty("params").GetProperty("parameters");
                        
                        Console.Error.WriteLine($"Executing tool: {toolName}");
                        
                        // Execute the tool by sending command to Rhino plugin via socket
                        var result = await ExecuteToolAsync(toolName, parameters);
                        
                        Console.Error.WriteLine($"Tool execution result: {result}");
                        
                        return JsonSerializer.Serialize(new
                        {
                            jsonrpc = "2.0",
                            id,
                            result = new
                            {
                                result
                            }
                        });
                        
                    case "shutdown":
                        Console.Error.WriteLine("Received shutdown request");
                        keepAlive = false;
                        return JsonSerializer.Serialize(new
                        {
                            jsonrpc = "2.0",
                            id,
                            result = new { success = true }
                        });
                        
                    default:
                        Console.Error.WriteLine($"Unknown method: {method}");
                        return JsonSerializer.Serialize(new
                        {
                            jsonrpc = "2.0",
                            id,
                            result = new { }
                        });
                }
            }
            catch (Exception ex)
            {
                Console.Error.WriteLine($"Error processing message: {ex.Message}");
                Console.Error.WriteLine($"Stack trace: {ex.StackTrace}");
                return JsonSerializer.Serialize(new
                {
                    jsonrpc = "2.0",
                    id = 0,
                    error = new
                    {
                        code = -32603,
                        message = $"Internal error: {ex.Message}"
                    }
                });
            }
        }
        
        private async Task<string> ExecuteToolAsync(string toolName, JsonElement parameters)
        {
            if (string.IsNullOrEmpty(toolName))
            {
                Console.Error.WriteLine("WARNING: Tool name is null or empty");
                return JsonSerializer.Serialize(new { error = "Tool name cannot be null or empty" });
            }
            
            string commandType = "";
            
            // Map tool name to command type
            if (toolName.StartsWith("geometry_tools."))
            {
                commandType = toolName.Replace("geometry_tools.", "");
            }
            else if (toolName.StartsWith("scene_tools."))
            {
                commandType = toolName.Replace("scene_tools.", "");
            }
            
            // Create command object
            var command = new
            {
                Type = commandType,
                Params = parameters
            };
            
            try
            {
                Console.Error.WriteLine($"Connecting to Rhino socket server on localhost:{PORT}");
                using (var client = new TcpClient("localhost", PORT))
                {
                    var stream = client.GetStream();
                    
                    // Send command
                    var commandJson = JsonSerializer.Serialize(command);
                    Console.Error.WriteLine($"Sending command: {commandJson}");
                    var buffer = Encoding.UTF8.GetBytes(commandJson);
                    await stream.WriteAsync(buffer, 0, buffer.Length);
                    
                    // Read response
                    buffer = new byte[4096];
                    int bytesRead = await stream.ReadAsync(buffer, 0, buffer.Length);
                    var response = Encoding.UTF8.GetString(buffer, 0, bytesRead);
                    Console.Error.WriteLine($"Received response: {response}");
                    
                    return response;
                }
            }
            catch (Exception ex)
            {
                Console.Error.WriteLine($"Error executing tool: {ex.Message}");
                Console.Error.WriteLine($"Stack trace: {ex.StackTrace}");
                return $"{{\"error\": \"{ex.Message.Replace("\"", "\\\"").Replace("\n", "\\n")}\"}}";
            }
        }
    }
}
