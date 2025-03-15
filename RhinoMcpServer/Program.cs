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
        private static object _consoleLock = new object();
        private static bool _shuttingDown = false;
        
        static async Task Main(string[] args)
        {
            // Critical: Use a custom TextWriter for Console.Out to avoid any stdout output
            // This ensures we never accidentally write to stdout except through our controlled writer
            var originalOut = Console.Out;
            Console.SetOut(TextWriter.Null);
            
            try
            {
                // Use Console.Error for ALL logging
                lock (_consoleLock)
                {
                    Console.Error.WriteLine("RhinoMcpServer: Starting...");
                }
                
                // Attach shutdown handlers to prevent premature exit
                AppDomain.CurrentDomain.ProcessExit += (s, e) => 
                {
                    lock (_consoleLock)
                    {
                        Console.Error.WriteLine("Process exit event triggered, shutting down...");
                    }
                    _shuttingDown = true;
                    _exitEvent.Set();
                };
                
                AppDomain.CurrentDomain.UnhandledException += (s, e) =>
                {
                    lock (_consoleLock)
                    {
                        Console.Error.WriteLine($"CRITICAL: Unhandled exception: {e.ExceptionObject}");
                    }
                    _shuttingDown = true;
                    _exitEvent.Set();
                };
                
                Console.CancelKeyPress += (s, e) =>
                {
                    lock (_consoleLock)
                    {
                        Console.Error.WriteLine("Ctrl+C detected, shutting down gracefully...");
                    }
                    e.Cancel = true; // Don't terminate process immediately
                    _shuttingDown = true;
                    _exitEvent.Set();
                };
                
                // Initialize MCP protocol handlers with explicit streams
                var server = new McpServer(Console.OpenStandardInput(), originalOut);
                
                // Start the server in a background task
                var serverTask = Task.Run(async () => 
                {
                    try 
                    {
                        await server.StartAsync();
                    } 
                    catch (Exception ex)
                    {
                        lock (_consoleLock)
                        {
                            Console.Error.WriteLine($"Fatal server error: {ex.Message}");
                            Console.Error.WriteLine(ex.StackTrace);
                        }
                        _shuttingDown = true;
                        _exitEvent.Set();
                    }
                });
                
                // Don't wait for a key if we're being run by Claude Desktop
                // Only show this message when run manually for debugging
                if (args.Length > 0 && args[0] == "--debug")
                {
                    lock (_consoleLock)
                    {
                        Console.Error.WriteLine("RhinoMcpServer: Press any key to exit");
                    }
                    Console.ReadKey();
                    _shuttingDown = true;
                    _exitEvent.Set();
                }
                else
                {
                    // Log that we're waiting for events
                    lock (_consoleLock)
                    {
                        Console.Error.WriteLine("RhinoMcpServer: Running and waiting for MCP messages...");
                    }
                    
                    // Block until the exit event is set
                    _exitEvent.WaitOne();
                    
                    // Give the server a chance to cleanly shut down
                    if (!serverTask.IsCompleted)
                    {
                        lock (_consoleLock)
                        {
                            Console.Error.WriteLine("Waiting for server to finish processing...");
                        }
                        await Task.WhenAny(serverTask, Task.Delay(3000)); // Wait up to 3 seconds
                    }
                    
                    lock (_consoleLock)
                    {
                        Console.Error.WriteLine("RhinoMcpServer: Exiting gracefully");
                    }
                }
            }
            catch (Exception ex)
            {
                lock (_consoleLock)
                {
                    Console.Error.WriteLine($"FATAL ERROR in main program loop: {ex.Message}");
                    Console.Error.WriteLine(ex.StackTrace);
                }
                // Exit with error code
                Environment.Exit(1);
            }
        }
    }
    
    class McpServer
    {
        private const int PORT = 9876;
        private readonly Stream _inputStream;
        private readonly TextWriter _outputWriter;
        private readonly object _consoleLock = new object();
        private bool _keepAlive = true;
        
        public McpServer(Stream inputStream, TextWriter outputWriter)
        {
            _inputStream = inputStream ?? throw new ArgumentNullException(nameof(inputStream));
            _outputWriter = outputWriter ?? throw new ArgumentNullException(nameof(outputWriter));
        }
        
        public async Task StartAsync()
        {
            lock (_consoleLock)
            {
                Console.Error.WriteLine("Initializing server...");
            }
            
            try
            {
                // Set up dedicated readers and writers for stdin/stdout
                var reader = new StreamReader(_inputStream);
                
                // Set up message handling with perpetual loop
                while (_keepAlive)
                {
                    try
                    {
                        var line = await reader.ReadLineAsync();
                        if (line == null)
                        {
                            lock (_consoleLock)
                            {
                                Console.Error.WriteLine("Input stream closed, exiting...");
                            }
                            break;
                        }
                        
                        lock (_consoleLock)
                        {
                            Console.Error.WriteLine($"Message from client: {line}");
                        }
                        
                        var response = await ProcessMcpMessage(line);
                        
                        // CRITICAL: Only write JSON responses to stdout
                        // We lock to ensure no other thread can write to stdout
                        await _outputWriter.WriteLineAsync(response);
                        await _outputWriter.FlushAsync();
                        
                        // Add a small delay to allow other operations to finish
                        await Task.Delay(50);
                    }
                    catch (Exception ex)
                    {
                        lock (_consoleLock)
                        {
                            Console.Error.WriteLine($"Error processing message: {ex.Message}");
                            Console.Error.WriteLine($"Stack trace: {ex.StackTrace}");
                        }
                        
                        try
                        {
                            // Try to send an error response
                            var errorResponse = JsonSerializer.Serialize(new
                            {
                                jsonrpc = "2.0",
                                id = 0,
                                error = new
                                {
                                    code = -32603,
                                    message = $"Internal error: {ex.Message}"
                                }
                            });
                            
                            await _outputWriter.WriteLineAsync(errorResponse);
                            await _outputWriter.FlushAsync();
                        }
                        catch (Exception innerEx)
                        {
                            lock (_consoleLock)
                            {
                                Console.Error.WriteLine($"Failed to send error response: {innerEx.Message}");
                            }
                        }
                        
                        // Don't break the loop for errors, keep trying to process messages
                    }
                }
            }
            catch (Exception ex)
            {
                lock (_consoleLock)
                {
                    Console.Error.WriteLine($"CRITICAL ERROR in StartAsync: {ex.Message}");
                    Console.Error.WriteLine($"Stack trace: {ex.StackTrace}");
                }
            }
            
            lock (_consoleLock)
            {
                Console.Error.WriteLine("Server shutting down...");
            }
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
                        lock (_consoleLock)
                        {
                            Console.Error.WriteLine("Server started and connected successfully");
                        }
                        
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
                        
                        lock (_consoleLock)
                        {
                            Console.Error.WriteLine($"Executing tool: {toolName}");
                        }
                        
                        // Execute the tool by sending command to Rhino plugin via socket
                        var result = await ExecuteToolAsync(toolName, parameters);
                        
                        lock (_consoleLock)
                        {
                            Console.Error.WriteLine($"Tool execution result: {result}");
                        }
                        
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
                        lock (_consoleLock)
                        {
                            Console.Error.WriteLine("Received shutdown request");
                        }
                        _keepAlive = false;
                        return JsonSerializer.Serialize(new
                        {
                            jsonrpc = "2.0",
                            id,
                            result = new { success = true }
                        });
                        
                    default:
                        lock (_consoleLock)
                        {
                            Console.Error.WriteLine($"Unknown method: {method}");
                        }
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
                lock (_consoleLock)
                {
                    Console.Error.WriteLine($"Error processing message: {ex.Message}");
                    Console.Error.WriteLine($"Stack trace: {ex.StackTrace}");
                }
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
                lock (_consoleLock)
                {
                    Console.Error.WriteLine("WARNING: Tool name is null or empty");
                }
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
                lock (_consoleLock)
                {
                    Console.Error.WriteLine($"Connecting to Rhino socket server on localhost:{PORT}");
                }
                
                using (var client = new TcpClient("localhost", PORT))
                {
                    var stream = client.GetStream();
                    
                    // Send command
                    var commandJson = JsonSerializer.Serialize(command);
                    lock (_consoleLock)
                    {
                        Console.Error.WriteLine($"Sending command: {commandJson}");
                    }
                    
                    var buffer = Encoding.UTF8.GetBytes(commandJson);
                    await stream.WriteAsync(buffer, 0, buffer.Length);
                    
                    // Read response
                    buffer = new byte[4096];
                    int bytesRead = await stream.ReadAsync(buffer, 0, buffer.Length);
                    var response = Encoding.UTF8.GetString(buffer, 0, bytesRead);
                    
                    lock (_consoleLock)
                    {
                        Console.Error.WriteLine($"Received response: {response}");
                    }
                    
                    return response;
                }
            }
            catch (Exception ex)
            {
                lock (_consoleLock)
                {
                    Console.Error.WriteLine($"Error executing tool: {ex.Message}");
                    Console.Error.WriteLine($"Stack trace: {ex.StackTrace}");
                }
                return $"{{\"error\": \"{ex.Message.Replace("\"", "\\\"").Replace("\n", "\\n")}\"}}";
            }
        }
    }
}
