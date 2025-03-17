using Rhino;
using Rhino.Commands;
using Rhino.PlugIns;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using NLog;

namespace RhinoMcpPlugin
{
    // Main plugin class
    public class RhinoMcpPluginCommand : PlugIn
    {
        private static readonly Logger Logger = LogManager.GetCurrentClassLogger();
        private SocketServer socketServer;
        private CommandHandlers commandHandlers;

        public override PlugInLoadTime LoadTime => PlugInLoadTime.AtStartup;

        public RhinoMcpPluginCommand()
        {
            Instance = this;
        }

        public static RhinoMcpPluginCommand Instance { get; private set; }

        protected override LoadReturnCode OnLoad(ref string errorMessage)
        {
            try
            {
                Logger.Info("RhinoMcpPlugin loading...");
                Logger.Info($"Rhino version: {RhinoApp.Version}");
                Logger.Info($"Current directory: {System.IO.Directory.GetCurrentDirectory()}");

                // Check document status
                var docCount = RhinoDoc.OpenDocuments().Length;
                Logger.Info($"Open document count: {docCount}");
                Logger.Info($"Active document: {(RhinoDoc.ActiveDoc != null ? "exists" : "null")}");

                // Create an empty document if none exists
                if (RhinoDoc.ActiveDoc == null)
                {
                    Logger.Info("No active document found. Creating a new document...");
                    RhinoApp.RunScript("_New", false);
                    
                    if (RhinoDoc.ActiveDoc == null)
                    {
                        Logger.Error("CRITICAL: Failed to create a new document");
                        errorMessage = "Failed to create a new Rhino document. The plugin requires an active document.";
                        return LoadReturnCode.FailedToLoad;
                    }
                    
                    Logger.Info($"New document created successfully: {RhinoDoc.ActiveDoc.Name}");
                }

                // Initialize command handlers
                commandHandlers = new CommandHandlers();
                
                // Initialize socket server
                socketServer = new SocketServer(commandHandlers);
                var success = socketServer.Start();
                Logger.Info($"Socket server started: {success}");
                
                // Register document events
                RhinoDoc.NewDocument += OnNewDocument;
                RhinoDoc.CloseDocument += OnCloseDocument;
                RhinoDoc.BeginOpenDocument += OnBeginOpenDocument;
                RhinoDoc.EndOpenDocument += OnEndOpenDocument;
                
                // Check all essential components
                var componentStatus = new Dictionary<string, bool> {
                    { "SocketServer", socketServer != null },
                    { "CommandHandlers", commandHandlers != null },
                    { "RhinoDoc", RhinoDoc.ActiveDoc != null }
                };
                
                foreach (var component in componentStatus)
                {
                    Logger.Info($"Component {component.Key}: {(component.Value ? "OK" : "NULL")}");
                }
                
                Logger.Info("RhinoMcpPlugin loaded successfully");
                return LoadReturnCode.Success;
            }
            catch (Exception ex)
            {
                Logger.Error(ex, $"Error during plugin load: {ex.Message}");
                errorMessage = ex.Message;
                return LoadReturnCode.FailedToLoad;
            }
        }

        protected override void OnShutdown()
        {
            try
            {
                Logger.Info("RhinoMcpPlugin shutting down...");
                
                // Unregister document events
                RhinoDoc.NewDocument -= OnNewDocument;
                RhinoDoc.CloseDocument -= OnCloseDocument;
                RhinoDoc.BeginOpenDocument -= OnBeginOpenDocument;
                RhinoDoc.EndOpenDocument -= OnEndOpenDocument;
                
                // Stop socket server
                if (socketServer != null)
                {
                    socketServer.Stop();
                    Logger.Info("Socket server stopped");
                }
                
                Logger.Info("RhinoMcpPlugin shutdown complete");
            }
            catch (Exception ex)
            {
                Logger.Error(ex, $"Error during plugin shutdown: {ex.Message}");
            }
        }
        
        private void OnNewDocument(object sender, DocumentEventArgs e)
        {
            Logger.Info($"New document created: {e.Document.Name}");
            Logger.Info($"Active document: {(RhinoDoc.ActiveDoc != null ? RhinoDoc.ActiveDoc.Name : "null")}");
        }
        
        private void OnCloseDocument(object sender, DocumentEventArgs e)
        {
            Logger.Info($"Document closed: {e.Document.Name}");
            Logger.Info($"Remaining open documents: {RhinoDoc.OpenDocuments().Length}");
            
            // If this was the last document, create a new one
            if (RhinoDoc.OpenDocuments().Length == 0)
            {
                Logger.Info("No documents remaining. Creating a new document...");
                RhinoApp.RunScript("_New", false);
                Logger.Info($"New document created: {(RhinoDoc.ActiveDoc != null ? RhinoDoc.ActiveDoc.Name : "null")}");
            }
        }
        
        private void OnBeginOpenDocument(object sender, DocumentOpenEventArgs e)
        {
            Logger.Info($"Beginning to open document: {e.FileName}");
        }
        
        private void OnEndOpenDocument(object sender, DocumentOpenEventArgs e)
        {
            Logger.Info($"Finished opening document: {e.Document.Name}");
        }
    }

    // Socket server class to handle communication
    public class SocketServer
    {
        private static readonly Logger Logger = LogManager.GetCurrentClassLogger();
        private TcpListener server;
        private bool isRunning;
        private CommandHandlers commandHandlers;
        private CancellationTokenSource cancellationTokenSource;

        public bool IsRunning => isRunning;

        public SocketServer(CommandHandlers handlers)
        {
            commandHandlers = handlers;
            cancellationTokenSource = new CancellationTokenSource();
        }

        public bool Start(int port = 9876)
        {
            try
            {
                Logger.Info($"Socket server initializing on port {port}");
                server = new TcpListener(IPAddress.Loopback, port);
                server.Start();
                isRunning = true;

                // Start accepting clients in a background task
                Task.Run(() => AcceptClientsAsync(cancellationTokenSource.Token), cancellationTokenSource.Token);
                
                Logger.Info($"Socket server started successfully on port {port}");
                return true;
            }
            catch (Exception ex)
            {
                Logger.Error(ex, $"Failed to start socket server: {ex.Message}");
                return false;
            }
        }

        public void Stop()
        {
            try
            {
                Logger.Info("Stopping socket server...");
                isRunning = false;
                cancellationTokenSource.Cancel();
                server?.Stop();
                Logger.Info("Socket server stopped");
            }
            catch (Exception ex)
            {
                Logger.Error(ex, $"Error stopping socket server: {ex.Message}");
            }
        }

        private async Task AcceptClientsAsync(CancellationToken cancellationToken)
        {
            while (isRunning && !cancellationToken.IsCancellationRequested)
            {
                try
                {
                    var client = await server.AcceptTcpClientAsync();
                    Logger.Info($"Client connected from {client.Client.RemoteEndPoint}");

                    // Handle each client in a separate task
                    _ = Task.Run(() => HandleClientAsync(client, cancellationToken), cancellationToken);
                }
                catch (OperationCanceledException)
                {
                    // Normal cancellation, do nothing
                    Logger.Info("Client acceptance loop cancelled");
                    break;
                }
                catch (Exception ex)
                {
                    Logger.Error(ex, $"Error accepting client: {ex.Message}");
                    // Short delay before trying again
                    await Task.Delay(1000, cancellationToken);
                }
            }
        }

        private async Task HandleClientAsync(TcpClient client, CancellationToken cancellationToken)
        {
            using (client)
            {
                try
                {
                    using (var stream = client.GetStream())
                    {
                        var buffer = new byte[4096];
                        while (isRunning && !cancellationToken.IsCancellationRequested)
                        {
                            // Read command from client
                            var data = new List<byte>();
                            int bytesRead;

                            do
                            {
                                bytesRead = await stream.ReadAsync(buffer, 0, buffer.Length, cancellationToken);
                                if (bytesRead > 0)
                                {
                                    data.AddRange(buffer.Take(bytesRead));
                                }
                            } while (stream.DataAvailable);

                            if (bytesRead == 0)
                            {
                                // Client disconnected
                                Logger.Info("Client disconnected");
                                break;
                            }

                            // Process command and send response
                            var commandJson = Encoding.UTF8.GetString(data.ToArray());
                            Logger.Info($"Received command: {commandJson}");

                            string responseJson = ProcessCommand(commandJson);
                            Logger.Debug($"Sending response: {responseJson}");
                            
                            var responseBytes = Encoding.UTF8.GetBytes(responseJson);
                            await stream.WriteAsync(responseBytes, 0, responseBytes.Length, cancellationToken);
                        }
                    }
                }
                catch (OperationCanceledException)
                {
                    // Normal cancellation
                    Logger.Info("Client handler cancelled");
                }
                catch (Exception ex)
                {
                    Logger.Error(ex, $"Error handling client: {ex.Message}");
                }
                finally
                {
                    try
                    {
                        client.Close();
                    }
                    catch { /* ignore */ }
                }
            }
        }

        private string ProcessCommand(string commandJson)
        {
            try
            {
                // Parse command JSON
                JObject command = JObject.Parse(commandJson);
                string commandType = command["type"]?.ToString().ToLowerInvariant();
                JObject parameters = command["params"] as JObject ?? new JObject();
                
                // Special case for health check
                if (commandType == "health_check")
                {
                    return commandHandlers.HandleHealthCheck(parameters);
                }
                
                // Ensure we have an active document before processing commands
                if (RhinoDoc.ActiveDoc == null)
                {
                    Logger.Error("CRITICAL: No active document available for command processing");
                    return JsonConvert.SerializeObject(new
                    {
                        error = "No active Rhino document. Please open a document before executing commands."
                    });
                }
                
                // Process regular commands
                switch (commandType)
                {
                    case "ping":
                        return JsonConvert.SerializeObject(new { result = "pong" });
                        
                    case "get_scene_info":
                        return commandHandlers.HandleGetSceneInfo(parameters);
                        
                    case "create_box":
                        return commandHandlers.HandleCreateBox(parameters);
                        
                    case "create_sphere":
                        return commandHandlers.HandleCreateSphere(parameters);
                        
                    case "create_cylinder":
                        return commandHandlers.HandleCreateCylinder(parameters);
                        
                    case "clear_scene":
                        return commandHandlers.HandleClearScene(parameters);
                        
                    case "create_layer":
                        return commandHandlers.HandleCreateLayer(parameters);
                        
                    default:
                        Logger.Warn($"Unknown command type: {commandType}");
                        return JsonConvert.SerializeObject(new { error = $"Unknown command type: {commandType}" });
                }
            }
            catch (NullReferenceException ex)
            {
                Logger.Error(ex, $"NULL REFERENCE processing command: {commandJson}");
                Logger.Error($"Stack trace: {ex.StackTrace}");
                Logger.Error($"Context: ActiveDoc={RhinoDoc.ActiveDoc != null}");
                return JsonConvert.SerializeObject(new { error = $"Error processing command: {ex.Message}" });
            }
            catch (Exception ex)
            {
                Logger.Error(ex, $"Error processing command: {ex.Message}");
                return JsonConvert.SerializeObject(new { error = $"Error processing command: {ex.Message}" });
            }
        }
    }

    // Class to handle specific commands
    public class CommandHandlers
    {
        private static readonly Logger Logger = LogManager.GetCurrentClassLogger();

        public string HandleHealthCheck(JObject parameters)
        {
            try
            {
                Logger.Info("Performing health check...");
                
                var healthStatus = new Dictionary<string, object> {
                    { "PluginLoaded", true },
                    { "RhinoVersion", RhinoApp.Version.ToString() },
                    { "ActiveDocument", RhinoDoc.ActiveDoc != null },
                    { "OpenDocumentCount", RhinoDoc.OpenDocuments().Length },
                    { "SocketServerRunning", true },
                    { "MemoryUsage", System.GC.GetTotalMemory(false) / 1024 / 1024 + " MB" },
                    { "SdkVersion", typeof(RhinoApp).Assembly.GetName().Version.ToString() }
                };
                
                Logger.Info($"Health check results: {JsonConvert.SerializeObject(healthStatus)}");
                return JsonConvert.SerializeObject(new { 
                    success = true, 
                    result = healthStatus 
                });
            }
            catch (Exception ex)
            {
                Logger.Error(ex, $"Exception during health check: {ex.Message}");
                return JsonConvert.SerializeObject(new { 
                    error = $"Health check failed: {ex.Message}" 
                });
            }
        }

        public string HandleGetSceneInfo(JObject parameters)
        {
            Logger.Debug("Processing get_scene_info request");
            try
            {
                var doc = RhinoDoc.ActiveDoc;
                if (doc == null)
                {
                    Logger.Error("CRITICAL: RhinoDoc.ActiveDoc is NULL");
                    return JsonConvert.SerializeObject(new { 
                        error = "No active Rhino document. Please open a document first." 
                    });
                }
                
                Logger.Debug("Accessing document objects...");
                var objectCount = doc.Objects.Count;
                var layerCount = doc.Layers.Count;
                
                Logger.Info($"Retrieved scene info: {objectCount} objects, {layerCount} layers");
                return JsonConvert.SerializeObject(new { 
                    success = true, 
                    result = new {
                        objectCount = objectCount,
                        layerCount = layerCount,
                        documentName = doc.Name,
                        activeLayer = doc.Layers.CurrentLayer.Name
                    }
                });
            }
            catch (NullReferenceException ex)
            {
                Logger.Error(ex, $"NULL REFERENCE in get_scene_info: {ex.Message}");
                Logger.Error($"Stack trace: {ex.StackTrace}");
                return JsonConvert.SerializeObject(new { 
                    error = $"Error processing command: {ex.Message}" 
                });
            }
            catch (Exception ex)
            {
                Logger.Error(ex, $"Exception in get_scene_info: {ex.Message}");
                return JsonConvert.SerializeObject(new { 
                    error = $"Error getting scene info: {ex.Message}" 
                });
            }
        }

        public string HandleCreateBox(JObject parameters)
        {
            Logger.Debug($"Processing create_box with parameters: {parameters}");
            
            try
            {
                // Log parameter extraction
                Logger.Debug("Extracting parameters...");
                double cornerX = parameters.Value<double>("cornerX");
                double cornerY = parameters.Value<double>("cornerY");
                double cornerZ = parameters.Value<double>("cornerZ");
                double width = parameters.Value<double>("width");
                double depth = parameters.Value<double>("depth");
                double height = parameters.Value<double>("height");
                string color = parameters.Value<string>("color");
                
                // Log document access
                Logger.Debug("Accessing Rhino document...");
                var doc = RhinoDoc.ActiveDoc;
                if (doc == null)
                {
                    Logger.Error("CRITICAL: RhinoDoc.ActiveDoc is NULL");
                    return JsonConvert.SerializeObject(new { 
                        error = "No active Rhino document. Please open a document first." 
                    });
                }
                
                // Run on main UI thread
                bool success = false;
                object result = null;
                
                // Execute on the main Rhino UI thread
                RhinoApp.InvokeOnUiThread(new Action(() =>
                {
                    try
                    {
                        // Log geometric operations with safeguards
                        Logger.Debug("Creating geometry...");
                        var corner = new Rhino.Geometry.Point3d(cornerX, cornerY, cornerZ);
                        var box = new Rhino.Geometry.Box(
                            new Rhino.Geometry.Plane(corner, Rhino.Geometry.Vector3d.ZAxis),
                            new Rhino.Geometry.Interval(0, width),
                            new Rhino.Geometry.Interval(0, depth),
                            new Rhino.Geometry.Interval(0, height)
                        );
                        
                        // Verify box was created
                        if (box == null || !box.IsValid)
                        {
                            Logger.Error($"Box creation failed: {(box == null ? "null box" : "invalid box")}");
                            result = new { error = "Failed to create valid box geometry" };
                            return;
                        }
                        
                        // Log document modification
                        Logger.Debug("Adding to document...");
                        var id = doc.Objects.AddBox(box);
                        if (id == Guid.Empty)
                        {
                            Logger.Error("Failed to add box to document");
                            result = new { error = "Failed to add box to document" };
                            return;
                        }
                        
                        // Apply color if specified
                        if (!string.IsNullOrEmpty(color))
                        {
                            System.Drawing.Color objColor = System.Drawing.Color.FromName(color);
                            if (objColor.A > 0)
                            {
                                var objAttributes = new Rhino.DocObjects.ObjectAttributes();
                                objAttributes.ColorSource = Rhino.DocObjects.ObjectColorSource.ColorFromObject;
                                objAttributes.ObjectColor = objColor;
                                doc.Objects.ModifyAttributes(id, objAttributes, true);
                            }
                        }
                        
                        // Update views
                        doc.Views.Redraw();
                        
                        // Log successful operation
                        Logger.Info($"Successfully created box with ID {id}");
                        result = new { success = true, objectId = id.ToString() };
                        success = true;
                    }
                    catch (Exception ex)
                    {
                        Logger.Error(ex, $"Error in UI thread: {ex.Message}");
                        result = new { error = $"Error in UI thread: {ex.Message}" };
                    }
                }));
                
                if (success)
                {
                    return JsonConvert.SerializeObject(result);
                }
                else
                {
                    return JsonConvert.SerializeObject(result ?? new { error = "Unknown error creating box" });
                }
            }
            catch (NullReferenceException ex)
            {
                Logger.Error(ex, $"NULL REFERENCE in create_box: {ex.Message}");
                Logger.Error($"Stack trace: {ex.StackTrace}");
                return JsonConvert.SerializeObject(new { 
                    error = $"Error processing command: {ex.Message}" 
                });
            }
            catch (Exception ex)
            {
                Logger.Error(ex, $"Exception in create_box: {ex.Message}");
                return JsonConvert.SerializeObject(new { 
                    error = $"Error processing command: {ex.Message}" 
                });
            }
        }

        public string HandleCreateSphere(JObject parameters)
        {
            Logger.Debug($"Processing create_sphere with parameters: {parameters}");
            
            try
            {
                // Extract parameters
                Logger.Debug("Extracting parameters...");
                double centerX = parameters.Value<double>("centerX");
                double centerY = parameters.Value<double>("centerY");
                double centerZ = parameters.Value<double>("centerZ");
                double radius = parameters.Value<double>("radius");
                string color = parameters.Value<string>("color");
                
                // Access document
                Logger.Debug("Accessing Rhino document...");
                var doc = RhinoDoc.ActiveDoc;
                if (doc == null)
                {
                    Logger.Error("CRITICAL: RhinoDoc.ActiveDoc is NULL");
                    return JsonConvert.SerializeObject(new { 
                        error = "No active Rhino document. Please open a document first." 
                    });
                }
                
                // Execute on UI thread
                bool success = false;
                object result = null;
                
                RhinoApp.InvokeOnUiThread(new Action(() =>
                {
                    try
                    {
                        // Create geometry
                        Logger.Debug("Creating sphere geometry...");
                        var center = new Rhino.Geometry.Point3d(centerX, centerY, centerZ);
                        var sphere = new Rhino.Geometry.Sphere(center, radius);
                        
                        if (!sphere.IsValid)
                        {
                            Logger.Error("Invalid sphere geometry");
                            result = new { error = "Failed to create valid sphere geometry" };
                            return;
                        }
                        
                        // Add to document
                        Logger.Debug("Adding sphere to document...");
                        var id = doc.Objects.AddSphere(sphere);
                        if (id == Guid.Empty)
                        {
                            Logger.Error("Failed to add sphere to document");
                            result = new { error = "Failed to add sphere to document" };
                            return;
                        }
                        
                        // Apply color if specified
                        if (!string.IsNullOrEmpty(color))
                        {
                            System.Drawing.Color objColor = System.Drawing.Color.FromName(color);
                            if (objColor.A > 0)
                            {
                                var objAttributes = new Rhino.DocObjects.ObjectAttributes();
                                objAttributes.ColorSource = Rhino.DocObjects.ObjectColorSource.ColorFromObject;
                                objAttributes.ObjectColor = objColor;
                                doc.Objects.ModifyAttributes(id, objAttributes, true);
                            }
                        }
                        
                        // Update views
                        doc.Views.Redraw();
                        
                        Logger.Info($"Successfully created sphere with ID {id}");
                        result = new { success = true, objectId = id.ToString() };
                        success = true;
                    }
                    catch (Exception ex)
                    {
                        Logger.Error(ex, $"Error in UI thread: {ex.Message}");
                        result = new { error = $"Error in UI thread: {ex.Message}" };
                    }
                }));
                
                if (success)
                {
                    return JsonConvert.SerializeObject(result);
                }
                else
                {
                    return JsonConvert.SerializeObject(result ?? new { error = "Unknown error creating sphere" });
                }
            }
            catch (Exception ex)
            {
                Logger.Error(ex, $"Exception in create_sphere: {ex.Message}");
                return JsonConvert.SerializeObject(new { 
                    error = $"Error creating sphere: {ex.Message}" 
                });
            }
        }

        public string HandleCreateCylinder(JObject parameters)
        {
            Logger.Debug($"Processing create_cylinder with parameters: {parameters}");
            
            try
            {
                // Extract parameters
                double baseX = parameters.Value<double>("baseX");
                double baseY = parameters.Value<double>("baseY");
                double baseZ = parameters.Value<double>("baseZ");
                double height = parameters.Value<double>("height");
                double radius = parameters.Value<double>("radius");
                string color = parameters.Value<string>("color");
                
                // Access document
                var doc = RhinoDoc.ActiveDoc;
                if (doc == null)
                {
                    Logger.Error("CRITICAL: RhinoDoc.ActiveDoc is NULL");
                    return JsonConvert.SerializeObject(new { 
                        error = "No active Rhino document. Please open a document first." 
                    });
                }
                
                // Execute on UI thread
                bool success = false;
                object result = null;
                
                RhinoApp.InvokeOnUiThread(new Action(() =>
                {
                    try
                    {
                        // Create geometry
                        var basePt = new Rhino.Geometry.Point3d(baseX, baseY, baseZ);
                        var topPt = new Rhino.Geometry.Point3d(baseX, baseY, baseZ + height);
                        var cylinder = new Rhino.Geometry.Cylinder(
                            new Rhino.Geometry.Circle(basePt, radius),
                            height
                        );
                        
                        if (!cylinder.IsValid)
                        {
                            Logger.Error("Invalid cylinder geometry");
                            result = new { error = "Failed to create valid cylinder geometry" };
                            return;
                        }
                        
                        // Add to document
                        var id = doc.Objects.AddCylinder(cylinder);
                        if (id == Guid.Empty)
                        {
                            Logger.Error("Failed to add cylinder to document");
                            result = new { error = "Failed to add cylinder to document" };
                            return;
                        }
                        
                        // Apply color if specified
                        if (!string.IsNullOrEmpty(color))
                        {
                            System.Drawing.Color objColor = System.Drawing.Color.FromName(color);
                            if (objColor.A > 0)
                            {
                                var objAttributes = new Rhino.DocObjects.ObjectAttributes();
                                objAttributes.ColorSource = Rhino.DocObjects.ObjectColorSource.ColorFromObject;
                                objAttributes.ObjectColor = objColor;
                                doc.Objects.ModifyAttributes(id, objAttributes, true);
                            }
                        }
                        
                        // Update views
                        doc.Views.Redraw();
                        
                        Logger.Info($"Successfully created cylinder with ID {id}");
                        result = new { success = true, objectId = id.ToString() };
                        success = true;
                    }
                    catch (Exception ex)
                    {
                        Logger.Error(ex, $"Error in UI thread: {ex.Message}");
                        result = new { error = $"Error in UI thread: {ex.Message}" };
                    }
                }));
                
                if (success)
                {
                    return JsonConvert.SerializeObject(result);
                }
                else
                {
                    return JsonConvert.SerializeObject(result ?? new { error = "Unknown error creating cylinder" });
                }
            }
            catch (Exception ex)
            {
                Logger.Error(ex, $"Exception in create_cylinder: {ex.Message}");
                return JsonConvert.SerializeObject(new { 
                    error = $"Error creating cylinder: {ex.Message}" 
                });
            }
        }

        public string HandleClearScene(JObject parameters)
        {
            Logger.Debug($"Processing clear_scene with parameters: {parameters}");
            
            try
            {
                bool currentLayerOnly = parameters.Value<bool>("currentLayerOnly");
                
                // Access document
                var doc = RhinoDoc.ActiveDoc;
                if (doc == null)
                {
                    Logger.Error("CRITICAL: RhinoDoc.ActiveDoc is NULL");
                    return JsonConvert.SerializeObject(new { 
                        error = "No active Rhino document. Please open a document first." 
                    });
                }
                
                // Execute on UI thread
                bool success = false;
                object result = null;
                
                RhinoApp.InvokeOnUiThread(new Action(() =>
                {
                    try
                    {
                        int deletedCount = 0;
                        
                        if (currentLayerOnly)
                        {
                            // Get current layer index
                            int currentLayerIndex = doc.Layers.CurrentLayerIndex;
                            
                            // Delete objects on current layer
                            var objectsToDelete = new List<Guid>();
                            foreach (var rhObj in doc.Objects)
                            {
                                if (rhObj.Attributes.LayerIndex == currentLayerIndex)
                                {
                                    objectsToDelete.Add(rhObj.Id);
                                    deletedCount++;
                                }
                            }
                            
                            foreach (var id in objectsToDelete)
                            {
                                doc.Objects.Delete(id, true);
                            }
                            
                            Logger.Info($"Deleted {deletedCount} objects from current layer");
                        }
                        else
                        {
                            // Delete all objects
                            deletedCount = doc.Objects.Count;
                            doc.Objects.Clear();
                            Logger.Info($"Cleared all {deletedCount} objects from document");
                        }
                        
                        // Update views
                        doc.Views.Redraw();
                        
                        result = new { 
                            success = true, 
                            deletedCount = deletedCount,
                            currentLayerOnly = currentLayerOnly
                        };
                        success = true;
                    }
                    catch (Exception ex)
                    {
                        Logger.Error(ex, $"Error in UI thread: {ex.Message}");
                        result = new { error = $"Error in UI thread: {ex.Message}" };
                    }
                }));
                
                if (success)
                {
                    return JsonConvert.SerializeObject(result);
                }
                else
                {
                    return JsonConvert.SerializeObject(result ?? new { error = "Unknown error clearing scene" });
                }
            }
            catch (Exception ex)
            {
                Logger.Error(ex, $"Exception in clear_scene: {ex.Message}");
                return JsonConvert.SerializeObject(new { 
                    error = $"Error clearing scene: {ex.Message}" 
                });
            }
        }

        public string HandleCreateLayer(JObject parameters)
        {
            Logger.Debug($"Processing create_layer with parameters: {parameters}");
            
            try
            {
                string name = parameters.Value<string>("name");
                string color = parameters.Value<string>("color");
                
                if (string.IsNullOrEmpty(name))
                {
                    Logger.Error("Layer name is required");
                    return JsonConvert.SerializeObject(new { 
                        error = "Layer name is required" 
                    });
                }
                
                // Access document
                var doc = RhinoDoc.ActiveDoc;
                if (doc == null)
                {
                    Logger.Error("CRITICAL: RhinoDoc.ActiveDoc is NULL");
                    return JsonConvert.SerializeObject(new { 
                        error = "No active Rhino document. Please open a document first." 
                    });
                }
                
                // Execute on UI thread
                bool success = false;
                object result = null;
                
                RhinoApp.InvokeOnUiThread(new Action(() =>
                {
                    try
                    {
                        // Check if layer already exists
                        int existingIndex = doc.Layers.Find(name, true);
                        if (existingIndex >= 0)
                        {
                            Logger.Warning($"Layer '{name}' already exists");
                            var layer = doc.Layers[existingIndex];
                            result = new { 
                                success = true, 
                                layerId = layer.Id.ToString(),
                                layerName = layer.Name,
                                alreadyExisted = true
                            };
                            doc.Layers.SetCurrentLayerIndex(existingIndex, true);
                            success = true;
                            return;
                        }
                        
                        // Create new layer
                        var newLayer = new Rhino.DocObjects.Layer();
                        newLayer.Name = name;
                        
                        // Set color if specified
                        if (!string.IsNullOrEmpty(color))
                        {
                            System.Drawing.Color layerColor = System.Drawing.Color.FromName(color);
                            if (layerColor.A > 0)
                            {
                                newLayer.Color = layerColor;
                            }
                        }
                        
                        // Add layer to document
                        int index = doc.Layers.Add(newLayer);
                        if (index < 0)
                        {
                            Logger.Error($"Failed to add layer '{name}' to document");
                            result = new { error = $"Failed to add layer '{name}' to document" };
                            return;
                        }
                        
                        // Set as current layer
                        doc.Layers.SetCurrentLayerIndex(index, true);
                        
                        Logger.Info($"Successfully created layer '{name}' with index {index}");
                        result = new { 
                            success = true, 
                            layerId = newLayer.Id.ToString(),
                            layerName = newLayer.Name,
                            layerIndex = index
                        };
                        success = true;
                    }
                    catch (Exception ex)
                    {
                        Logger.Error(ex, $"Error in UI thread: {ex.Message}");
                        result = new { error = $"Error in UI thread: {ex.Message}" };
                    }
                }));
                
                if (success)
                {
                    return JsonConvert.SerializeObject(result);
                }
                else
                {
                    return JsonConvert.SerializeObject(result ?? new { error = $"Unknown error creating layer '{name}'" });
                }
            }
            catch (Exception ex)
            {
                Logger.Error(ex, $"Exception in create_layer: {ex.Message}");
                return JsonConvert.SerializeObject(new { 
                    error = $"Error creating layer: {ex.Message}" 
                });
            }
        }
    }
} 