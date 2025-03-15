using System;
using System.Collections.Generic;
using System.IO;
using System.Net;
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
        private static TextWriter _originalOut;
        private static StreamWriter _jsonResponseWriter;
        private static bool _isStdoutRedirected = false;
        private static StreamWriter _logFileWriter = null;
        private static int _pid = 0;
        
        static async Task Main(string[] args)
        {
            try
            {
                // CRITICAL: Immediately ensure we don't write logs to stdout
                _originalOut = Console.Out;
                _pid = System.Diagnostics.Process.GetCurrentProcess().Id;
                
                // Create a log directory if it doesn't exist
                string logDir = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "logs");
                Directory.CreateDirectory(logDir);
                
                // Create a log file with timestamp and PID
                string timestamp = DateTime.Now.ToString("yyyyMMdd_HHmmss");
                string logFilePath = Path.Combine(logDir, $"rhinoMcpServer_{timestamp}_{_pid}.log");
                
                // Open log file
                _logFileWriter = new StreamWriter(logFilePath, true) { AutoFlush = true };
                
                // Create stderr log prefix for better diagnosis
                var logPrefix = $"[RhinoMCP {_pid}] ";
                
                // Log startup message to both stderr and file
                string startupMsg = $"{logPrefix}Starting up...";
                Console.Error.WriteLine(startupMsg);
                Console.Error.Flush();
                _logFileWriter.WriteLine($"[{DateTime.Now:yyyy-MM-dd HH:mm:ss.fff}] {startupMsg}");
                
                // CRITICAL: Redirect Console.Out to prevent ANY accidental stdout writes
                Console.SetOut(TextWriter.Null);
                _isStdoutRedirected = true;
                
                // Create a dedicated writer for JSON responses only
                _jsonResponseWriter = new StreamWriter(Console.OpenStandardOutput()) { AutoFlush = true };
                
                // All logging must use Console.Error
                LogToStdErr($"RhinoMcpServer starting...");
                LogToStdErr($"Process ID: {_pid}");
                LogToStdErr($".NET Runtime: {System.Runtime.InteropServices.RuntimeInformation.FrameworkDescription}");
                LogToStdErr($"Current directory: {Environment.CurrentDirectory}");
                LogToStdErr($"Log file: {logFilePath}");
                
                // Set up Ctrl+C handler - but NOT client disconnect handlers
                // The client (Claude) may disconnect and reconnect as needed - this is NORMAL
                Console.CancelKeyPress += (s, e) =>
                {
                    LogToStdErr("Ctrl+C detected");
                    e.Cancel = true; // Don't terminate immediately
                    SignalShutdown("User Ctrl+C");
                };
                
                // Handle unhandled exceptions
                AppDomain.CurrentDomain.UnhandledException += (s, e) =>
                {
                    LogToStdErr($"CRITICAL: Unhandled exception: {e.ExceptionObject}");
                    SignalShutdown("Unhandled exception");
                };
                
                // CRITICAL: We need to ignore process.exit events from client disconnects
                // The MCP protocol design has clients that connect, get tools, and then disconnect
                // They only reconnect when they need to invoke a tool
                
                // Start the MCP server
                var server = new McpServer(_jsonResponseWriter);
                
                // Run the server in a background task and track its state
                var serverTask = Task.Run(async () => 
                {
                    try 
                    {
                        await server.StartAsync();
                    } 
                    catch (Exception ex)
                    {
                        LogToStdErr($"FATAL SERVER ERROR: {ex.Message}");
                        LogToStdErr(ex.StackTrace ?? "No stack trace available");
                        SignalShutdown("Server error");
                    }
                });
                
                // Only show debug message when run manually
                if (args.Length > 0 && args[0] == "--debug")
                {
                    LogToStdErr("DEBUG MODE: Press any key to exit");
                    Console.ReadKey();
                    SignalShutdown("User key press");
                }
                else
                {
                    LogToStdErr("Server initialized and waiting for MCP messages");
                    
                    // Keep the main thread alive indefinitely
                    // Only shutdown via explicit signal
                    _exitEvent.WaitOne();
                    
                    // Give server tasks time to complete cleanly
                    if (!serverTask.IsCompleted)
                    {
                        LogToStdErr("Waiting for server to complete all pending tasks...");
                        await Task.WhenAny(serverTask, Task.Delay(5000)); // 5 second timeout
                    }
                }
                
                LogToStdErr("Clean shutdown complete");
            }
            catch (Exception ex)
            {
                string errorMsg = $"FATAL PROGRAM ERROR: {ex.Message}";
                Console.Error.WriteLine(errorMsg);
                Console.Error.WriteLine(ex.StackTrace ?? "No stack trace available");
                Console.Error.Flush();
                
                // Try to log to file if available
                try 
                {
                    if (_logFileWriter != null)
                    {
                        _logFileWriter.WriteLine($"[{DateTime.Now:yyyy-MM-dd HH:mm:ss.fff}] {errorMsg}");
                        _logFileWriter.WriteLine(ex.StackTrace ?? "No stack trace available");
                        _logFileWriter.Flush();
                        _logFileWriter.Close();
                    }
                }
                catch 
                {
                    // Just ignore errors in logging at this point
                }
                
                Environment.Exit(1);
            }
            finally
            {
                // Close log file if open
                if (_logFileWriter != null)
                {
                    try
                    {
                        _logFileWriter.Close();
                    }
                    catch
                    {
                        // Ignore errors when closing
                    }
                }
            }
        }

        // Thread-safe stderr logging
        private static void LogToStdErr(string message)
        {
            lock (_consoleLock)
            {
                string timestamp = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss.fff");
                
                // Write to stderr
                Console.Error.WriteLine(message);
                Console.Error.Flush(); // Ensure logs are flushed immediately
                
                // Also write to log file if available
                try
                {
                    if (_logFileWriter != null)
                    {
                        _logFileWriter.WriteLine($"[{timestamp}] {message}");
                        _logFileWriter.Flush();
                    }
                }
                catch
                {
                    // Just continue if log file writing fails
                }
            }
        }
        
        // Central shutdown method
        private static void SignalShutdown(string reason)
        {
            if (!_shuttingDown)
            {
                _shuttingDown = true;
                LogToStdErr($"Shutting down, reason: {reason}");
                _exitEvent.Set();
            }
        }
    }
    
    class McpServer
    {
        private const int PORT = 9876;
        private readonly TextWriter _jsonWriter;
        private readonly object _consoleLock = new object();
        private bool _keepAlive = true;
        private bool _isShuttingDown = false;
        
        public McpServer(TextWriter jsonWriter)
        {
            _jsonWriter = jsonWriter ?? throw new ArgumentNullException(nameof(jsonWriter));
        }
        
        // Log to stderr with thread safety
        private void LogToStdErr(string message)
        {
            lock (_consoleLock)
            {
                Console.Error.WriteLine(message);
                Console.Error.Flush(); // Ensure logs are flushed immediately
                
                // Let the Program class handle file logging - it already
                // wraps our stderr output with timestamps
            }
        }
        
        // Write JSON response to stdout with thread safety
        private async Task WriteJsonResponseAsync(string jsonResponse)
        {
            if (string.IsNullOrEmpty(jsonResponse))
            {
                LogToStdErr("WARNING: Attempted to write null/empty JSON response");
                return;
            }
            
            try
            {
                // Verify it's valid JSON before sending
                JsonDocument.Parse(jsonResponse);
                
                // CRITICAL: Only write valid JSON to stdout, and nothing else
                lock (_consoleLock)
                {
                    // Log what we're sending to stderr for debugging
                    var truncatedJson = jsonResponse.Length > 100 
                        ? jsonResponse.Substring(0, 100) + "..." 
                        : jsonResponse;
                    LogToStdErr($"Sending JSON response: {truncatedJson}");
                    
                    // Write the actual JSON to stdout
                    _jsonWriter.WriteLine(jsonResponse);
                    _jsonWriter.Flush();
                }
            }
            catch (Exception ex)
            {
                LogToStdErr($"ERROR: Invalid JSON response: {ex.Message}");
                LogToStdErr($"Problematic JSON: {jsonResponse}");
            }
        }
        
        public async Task StartAsync()
        {
            LogToStdErr("MCP server initializing...");
            
            // Process stdin messages
            var stdinTask = ProcessStdinAsync();
            
            // Wait for completion (which should only happen on shutdown)
            await stdinTask;
            
            LogToStdErr("MCP server shutdown complete");
        }
        
        private async Task ProcessStdinAsync()
        {
            try
            {
                LogToStdErr("Starting stdin message processing");
                
                // Set up StreamReader for stdin with infinite timeout
                using (var reader = new StreamReader(Console.OpenStandardInput()))
                {
                    LogToStdErr("Server ready to process messages from stdin");
                    
                    // Process messages in a loop until shutdown
                    while (!_isShuttingDown && _keepAlive)
                    {
                        try
                        {
                            // Read the next line from stdin
                            string line = null;
                            
                            try
                            {
                                // Use ReadLineAsync with a timeout to handle EOF conditions
                                var readTask = reader.ReadLineAsync();
                                var completedTask = await Task.WhenAny(readTask, Task.Delay(10000)); // 10-second timeout
                                
                                if (completedTask == readTask)
                                {
                                    line = await readTask;
                                }
                                else
                                {
                                    // Timeout occurred - could be waiting for a new connection
                                    LogToStdErr("No input received in 10 seconds, waiting...");
                                    continue;
                                }
                            }
                            catch (Exception ex)
                            {
                                LogToStdErr($"Error reading from stdin: {ex.Message}");
                                // Sleep to prevent tight loop if stdin errors
                                await Task.Delay(1000);
                                continue;
                            }
                            
                            // Check for EOF or disconnected client
                            if (line == null)
                            {
                                LogToStdErr("Input stream EOF - Claude client disconnected");
                                LogToStdErr("This is normal behavior - waiting for reconnection");
                                
                                // CRITICAL: Don't exit, just wait for Claude to reconnect
                                await Task.Delay(1000); // Prevent CPU spin
                                continue;
                            }
                            
                            // Skip empty lines
                            if (string.IsNullOrWhiteSpace(line))
                            {
                                await Task.Delay(10);
                                continue;
                            }
                            
                            // Log the message (truncated to avoid massive logs)
                            var truncatedInput = line.Length > 100 
                                ? line.Substring(0, 100) + "..." 
                                : line;
                            LogToStdErr($"Received message: {truncatedInput}");
                            
                            // Process the message and get response
                            var response = await ProcessMcpMessage(line);
                            
                            // Write the response to stdout
                            await WriteJsonResponseAsync(response);
                            
                            // Small delay to prevent CPU spinning
                            await Task.Delay(10);
                        }
                        catch (Exception ex)
                        {
                            LogToStdErr($"Error processing message: {ex.Message}");
                            LogToStdErr(ex.StackTrace ?? "No stack trace available");
                            
                            try
                            {
                                // Send error response
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
                                
                                await WriteJsonResponseAsync(errorResponse);
                            }
                            catch (Exception innerEx)
                            {
                                LogToStdErr($"Failed to send error response: {innerEx.Message}");
                            }
                            
                            // Don't exit the loop on error, keep waiting for more messages
                            await Task.Delay(100); // Small delay to prevent tight loop on errors
                        }
                    }
                }
                
                LogToStdErr("Message processing loop exited");
            }
            catch (Exception ex)
            {
                LogToStdErr($"CRITICAL ERROR in stdin processing: {ex.Message}");
                LogToStdErr(ex.StackTrace ?? "No stack trace available");
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
                        LogToStdErr("Processing initialize request");
                        
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
                        
                        LogToStdErr($"Executing tool: {toolName}");
                        
                        // Execute the tool by sending command to Rhino plugin via socket
                        var result = await ExecuteToolAsync(toolName, parameters);
                        
                        LogToStdErr($"Tool execution result: {result}");
                        
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
                        LogToStdErr("Received shutdown request");
                        _isShuttingDown = true;
                        _keepAlive = false;
                        
                        return JsonSerializer.Serialize(new
                        {
                            jsonrpc = "2.0",
                            id,
                            result = new { success = true }
                        });
                        
                    default:
                        LogToStdErr($"Unknown method: {method}");
                        return JsonSerializer.Serialize(new
                        {
                            jsonrpc = "2.0",
                            id,
                            error = new
                            {
                                code = -32601,
                                message = $"Method not found: {method}"
                            }
                        });
                }
            }
            catch (Exception ex)
            {
                LogToStdErr($"Error processing message: {ex.Message}");
                LogToStdErr(ex.StackTrace ?? "No stack trace available");
                
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
                LogToStdErr("WARNING: Tool name is null or empty");
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
                LogToStdErr($"Connecting to Rhino socket server on localhost:{PORT}");
                
                using (var client = new TcpClient())
                {
                    // Set up timeouts to prevent hanging
                    client.ReceiveTimeout = 30000; // 30-second timeout
                    client.SendTimeout = 30000;
                    
                    // Connect with timeout
                    var connectTask = client.ConnectAsync("localhost", PORT);
                    if (await Task.WhenAny(connectTask, Task.Delay(10000)) != connectTask)
                    {
                        LogToStdErr("Connection to Rhino socket server timed out");
                        return JsonSerializer.Serialize(new { error = "Connection to Rhino socket server timed out after 10 seconds" });
                    }
                    
                    var stream = client.GetStream();
                    
                    // Send command
                    var commandJson = JsonSerializer.Serialize(command);
                    LogToStdErr($"Sending command: {commandJson}");
                    
                    var buffer = Encoding.UTF8.GetBytes(commandJson);
                    await stream.WriteAsync(buffer, 0, buffer.Length);
                    
                    // Read response with timeout
                    buffer = new byte[16384]; // Larger buffer for bigger responses
                    
                    var readTask = stream.ReadAsync(buffer, 0, buffer.Length);
                    if (await Task.WhenAny(readTask, Task.Delay(30000)) != readTask)
                    {
                        LogToStdErr("Reading response from Rhino socket server timed out");
                        return JsonSerializer.Serialize(new { error = "Reading response from Rhino socket server timed out after 30 seconds" });
                    }
                    
                    int bytesRead = await readTask;
                    var response = Encoding.UTF8.GetString(buffer, 0, bytesRead);
                    
                    LogToStdErr($"Received response: {response}");
                    
                    return response;
                }
            }
            catch (Exception ex)
            {
                LogToStdErr($"Error executing tool: {ex.Message}");
                LogToStdErr(ex.StackTrace ?? "No stack trace available");
                return $"{{\"error\": \"{ex.Message.Replace("\"", "\\\"").Replace("\n", "\\n")}\"}}";
            }
        }
    }
}
