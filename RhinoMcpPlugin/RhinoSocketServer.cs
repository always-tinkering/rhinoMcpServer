using System;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using Rhino;
using Rhino.Commands;

namespace RhinoMcpPlugin
{
    public class RhinoSocketServer
    {
        private TcpListener _listener;
        private bool _isRunning;
        private readonly int _port;
        private readonly ManualResetEvent _stopEvent = new ManualResetEvent(false);
        
        // Default port for communication
        public RhinoSocketServer(int port = 9876)
        {
            _port = port;
        }
        
        public void Start()
        {
            if (_isRunning) return;
            
            _isRunning = true;
            _stopEvent.Reset();
            
            Task.Run(() => RunServer());
            
            RhinoApp.WriteLine($"RhinoMcpPlugin: Socket server started on port {_port}");
        }
        
        public void Stop()
        {
            if (!_isRunning) return;
            
            _isRunning = false;
            _listener?.Stop();
            _stopEvent.Set();
            
            RhinoApp.WriteLine("RhinoMcpPlugin: Socket server stopped");
        }
        
        private void RunServer()
        {
            try
            {
                _listener = new TcpListener(IPAddress.Loopback, _port);
                _listener.Start();
                
                while (_isRunning)
                {
                    // Set up listener to accept connection
                    var result = _listener.BeginAcceptTcpClient(AcceptCallback, _listener);
                    
                    // Wait for connection or stop signal
                    WaitHandle.WaitAny(new[] { _stopEvent, result.AsyncWaitHandle });
                    
                    if (!_isRunning) break;
                }
            }
            catch (Exception ex)
            {
                RhinoApp.WriteLine($"RhinoMcpPlugin: Socket server error: {ex.Message}");
            }
            finally
            {
                _listener?.Stop();
            }
        }
        
        private void AcceptCallback(IAsyncResult ar)
        {
            if (!_isRunning) return;
            
            TcpClient client = null;
            
            try
            {
                var listener = (TcpListener)ar.AsyncState;
                client = listener.EndAcceptTcpClient(ar);
                
                // Handle the client in a separate task
                Task.Run(() => HandleClient(client));
            }
            catch (ObjectDisposedException)
            {
                // Listener was stopped, ignore
            }
            catch (Exception ex)
            {
                RhinoApp.WriteLine($"RhinoMcpPlugin: Error accepting client: {ex.Message}");
                client?.Close();
            }
        }
        
        private void HandleClient(TcpClient client)
        {
            using (client)
            {
                try
                {
                    var stream = client.GetStream();
                    var buffer = new byte[4096];
                    
                    // Read message
                    int bytesRead = stream.Read(buffer, 0, buffer.Length);
                    if (bytesRead == 0) return;
                    
                    var message = Encoding.UTF8.GetString(buffer, 0, bytesRead);
                    RhinoApp.WriteLine($"RhinoMcpPlugin: Received command: {message}");
                    
                    // Parse and execute command
                    var response = ProcessCommand(message);
                    
                    // Send response
                    var responseBytes = Encoding.UTF8.GetBytes(response);
                    stream.Write(responseBytes, 0, responseBytes.Length);
                }
                catch (Exception ex)
                {
                    RhinoApp.WriteLine($"RhinoMcpPlugin: Error handling client: {ex.Message}");
                }
            }
        }
        
        private string ProcessCommand(string message)
        {
            try
            {
                var command = JsonSerializer.Deserialize<Command>(message);
                
                // Route command to appropriate tool
                switch (command.Type.ToLowerInvariant())
                {
                    case "create_sphere":
                        return Tools.GeometryTools.CreateSphere(
                            GetDoubleParam(command.Params, "centerX"),
                            GetDoubleParam(command.Params, "centerY"),
                            GetDoubleParam(command.Params, "centerZ"),
                            GetDoubleParam(command.Params, "radius"),
                            GetOptionalStringParam(command.Params, "color")
                        );
                    
                    case "create_box":
                        return Tools.GeometryTools.CreateBox(
                            GetDoubleParam(command.Params, "cornerX"),
                            GetDoubleParam(command.Params, "cornerY"),
                            GetDoubleParam(command.Params, "cornerZ"),
                            GetDoubleParam(command.Params, "width"),
                            GetDoubleParam(command.Params, "depth"),
                            GetDoubleParam(command.Params, "height"),
                            GetOptionalStringParam(command.Params, "color")
                        );
                    
                    case "create_cylinder":
                        return Tools.GeometryTools.CreateCylinder(
                            GetDoubleParam(command.Params, "baseX"),
                            GetDoubleParam(command.Params, "baseY"),
                            GetDoubleParam(command.Params, "baseZ"),
                            GetDoubleParam(command.Params, "height"),
                            GetDoubleParam(command.Params, "radius"),
                            GetOptionalStringParam(command.Params, "color")
                        );
                        
                    case "get_scene_info":
                        var sceneInfo = Tools.SceneTools.GetSceneInfo();
                        return JsonSerializer.Serialize(sceneInfo);
                        
                    case "clear_scene":
                        bool currentLayerOnly = GetOptionalBoolParam(command.Params, "currentLayerOnly", false);
                        return Tools.SceneTools.ClearScene(currentLayerOnly);
                        
                    case "create_layer":
                        return Tools.SceneTools.CreateLayer(
                            GetStringParam(command.Params, "name"),
                            GetOptionalStringParam(command.Params, "color")
                        );
                        
                    default:
                        return JsonSerializer.Serialize(new { error = $"Unknown command: {command.Type}" });
                }
            }
            catch (Exception ex)
            {
                return JsonSerializer.Serialize(new { error = $"Error processing command: {ex.Message}" });
            }
        }
        
        private double GetDoubleParam(JsonElement element, string name)
        {
            if (element.TryGetProperty(name, out var prop) && prop.ValueKind == JsonValueKind.Number)
            {
                return prop.GetDouble();
            }
            throw new ArgumentException($"Missing or invalid required parameter: {name}");
        }
        
        private string GetStringParam(JsonElement element, string name)
        {
            if (element.TryGetProperty(name, out var prop) && prop.ValueKind == JsonValueKind.String)
            {
                return prop.GetString();
            }
            throw new ArgumentException($"Missing or invalid required parameter: {name}");
        }
        
        private string GetOptionalStringParam(JsonElement element, string name)
        {
            if (element.TryGetProperty(name, out var prop) && prop.ValueKind == JsonValueKind.String)
            {
                return prop.GetString();
            }
            return null;
        }
        
        private bool GetOptionalBoolParam(JsonElement element, string name, bool defaultValue)
        {
            if (element.TryGetProperty(name, out var prop) && prop.ValueKind == JsonValueKind.True || prop.ValueKind == JsonValueKind.False)
            {
                return prop.GetBoolean();
            }
            return defaultValue;
        }
        
        private class Command
        {
            public string Type { get; set; }
            public JsonElement Params { get; set; }
        }
    }
} 