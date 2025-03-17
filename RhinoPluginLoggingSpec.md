# Rhino Plugin Logging Specification

This document outlines enhanced logging for the RhinoMcpPlugin to facilitate better diagnostics of null reference exceptions and other issues.

## Logging Framework

1. **Use NLog or log4net** - Both provide flexible logging with configurable outputs and formats.
2. **Output Location** - Write logs to `/Users/angerman/scratch/rhinoMcpServer/logs/plugin/` to integrate with our unified logging system.
3. **Log File Naming** - Use date-based naming: `plugin_YYYY-MM-DD.log`.
4. **Log Format** - Match the server format: `[timestamp] [level] [component] message`.

## Core Logging Components

### Socket Server Component

```csharp
// Add this at the top of your socket server class
private static readonly Logger Logger = LogManager.GetCurrentClassLogger();

// In the server initialization
Logger.Info("Socket server initializing on port 9876");

// When accepting connections
Logger.Info($"Client connected from {client.Client.RemoteEndPoint}");

// Before processing each command
Logger.Info($"Received command: {commandJson}");

// Add try/catch with detailed exception logging
try {
    // Process command
} catch (NullReferenceException ex) {
    Logger.Error(ex, $"NULL REFERENCE processing command: {commandJson}");
    Logger.Error($"Stack trace: {ex.StackTrace}");
    // Identify which object is null
    Logger.Error($"Context: Document={doc != null}, ActiveDoc={Rhino.RhinoDoc.ActiveDoc != null}");
    return JsonConvert.SerializeObject(new { error = $"Error processing command: {ex.Message}" });
}
```

### Command Handler Component

For each command handler method, add structured try/catch blocks:

```csharp
public string HandleCreateBox(JObject parameters) {
    Logger.Debug($"Processing create_box with parameters: {parameters}");
    
    try {
        // Log parameter extraction
        Logger.Debug("Extracting parameters...");
        double cornerX = parameters.Value<double>("cornerX");
        // ... other parameters ...
        
        // Log document access
        Logger.Debug("Accessing Rhino document...");
        var doc = Rhino.RhinoDoc.ActiveDoc;
        if (doc == null) {
            Logger.Error("CRITICAL: RhinoDoc.ActiveDoc is NULL");
            return JsonConvert.SerializeObject(new { 
                error = "No active Rhino document. Please open a document first." 
            });
        }
        
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
        if (box == null || !box.IsValid) {
            Logger.Error($"Box creation failed: {(box == null ? "null box" : "invalid box")}");
            return JsonConvert.SerializeObject(new { 
                error = "Failed to create valid box geometry" 
            });
        }
        
        // Log document modification
        Logger.Debug("Adding to document...");
        var id = doc.Objects.AddBox(box);
        if (id == Guid.Empty) {
            Logger.Error("Failed to add box to document");
            return JsonConvert.SerializeObject(new { 
                error = "Failed to add box to document" 
            });
        }
        
        // Log successful operation
        Logger.Info($"Successfully created box with ID {id}");
        return JsonConvert.SerializeObject(new { 
            success = true, 
            objectId = id.ToString() 
        });
    }
    catch (NullReferenceException ex) {
        Logger.Error(ex, $"NULL REFERENCE in create_box: {ex.Message}");
        Logger.Error($"Stack trace: {ex.StackTrace}");
        return JsonConvert.SerializeObject(new { 
            error = $"Error processing command: {ex.Message}" 
        });
    }
    catch (Exception ex) {
        Logger.Error(ex, $"Exception in create_box: {ex.Message}");
        return JsonConvert.SerializeObject(new { 
            error = $"Error processing command: {ex.Message}" 
        });
    }
}
```

### Plugin Initialization

Add detailed logging during plugin initialization to verify the environment:

```csharp
public override void OnLoad(ref string errorMessage) {
    try {
        Logger.Info("Plugin loading...");
        Logger.Info($"Rhino version: {Rhino.RhinoApp.Version}");
        Logger.Info($"Current directory: {System.IO.Directory.GetCurrentDirectory()}");
        
        // Check document status
        var docCount = Rhino.RhinoDoc.OpenDocuments().Length;
        Logger.Info($"Open document count: {docCount}");
        Logger.Info($"Active document: {(Rhino.RhinoDoc.ActiveDoc != null ? "exists" : "null")}");
        
        // Initialize socket server
        socketServer = new SocketServer();
        var success = socketServer.Start();
        Logger.Info($"Socket server started: {success}");
        
        // Check all essential components
        var componentStatus = new Dictionary<string, bool> {
            { "SocketServer", socketServer != null },
            { "CommandHandlers", commandHandlers != null },
            { "RhinoDoc", Rhino.RhinoDoc.ActiveDoc != null }
        };
        
        foreach (var component in componentStatus) {
            Logger.Info($"Component {component.Key}: {(component.Value ? "OK" : "NULL")}");
        }
        
        Logger.Info("Plugin loaded successfully");
    }
    catch (Exception ex) {
        Logger.Error(ex, $"Error during plugin load: {ex.Message}");
        errorMessage = ex.Message;
    }
}
```

## Document Lifecycle Monitoring

Add event handlers to monitor document open/close/new events:

```csharp
public override void OnLoad(ref string errorMessage) {
    // existing code...
    
    // Register document events
    Rhino.RhinoDoc.NewDocument += OnNewDocument;
    Rhino.RhinoDoc.CloseDocument += OnCloseDocument;
    Rhino.RhinoDoc.BeginOpenDocument += OnBeginOpenDocument;
    Rhino.RhinoDoc.EndOpenDocument += OnEndOpenDocument;
}

private void OnNewDocument(object sender, DocumentEventArgs e) {
    Logger.Info($"New document created: {e.Document.Name}");
    Logger.Info($"Active document: {(Rhino.RhinoDoc.ActiveDoc != null ? Rhino.RhinoDoc.ActiveDoc.Name : "null")}");
}

private void OnCloseDocument(object sender, DocumentEventArgs e) {
    Logger.Info($"Document closed: {e.Document.Name}");
    Logger.Info($"Remaining open documents: {Rhino.RhinoDoc.OpenDocuments().Length}");
}

private void OnBeginOpenDocument(object sender, DocumentOpenEventArgs e) {
    Logger.Info($"Beginning to open document: {e.FileName}");
}

private void OnEndOpenDocument(object sender, DocumentOpenEventArgs e) {
    Logger.Info($"Finished opening document: {e.Document.Name}");
}
```

## Socket Server Health Checks

Implement a health check command that verifies critical components:

```csharp
public string HandleHealthCheck(JObject parameters) {
    try {
        Logger.Info("Performing health check...");
        
        var healthStatus = new Dictionary<string, object> {
            { "PluginLoaded", true },
            { "RhinoVersion", Rhino.RhinoApp.Version.ToString() },
            { "ActiveDocument", Rhino.RhinoDoc.ActiveDoc != null },
            { "OpenDocumentCount", Rhino.RhinoDoc.OpenDocuments().Length },
            { "SocketServerRunning", socketServer != null && socketServer.IsRunning },
            { "MemoryUsage", System.GC.GetTotalMemory(false) / 1024 / 1024 + " MB" },
            { "SdkVersion", typeof(Rhino.RhinoApp).Assembly.GetName().Version.ToString() }
        };
        
        Logger.Info($"Health check results: {JsonConvert.SerializeObject(healthStatus)}");
        return JsonConvert.SerializeObject(new { 
            success = true, 
            result = healthStatus 
        });
    }
    catch (Exception ex) {
        Logger.Error(ex, $"Exception during health check: {ex.Message}");
        return JsonConvert.SerializeObject(new { 
            error = $"Health check failed: {ex.Message}" 
        });
    }
}
```

## Implementation Steps

1. Add NLog NuGet package to the plugin project.
2. Create an NLog configuration file that outputs to our logs directory.
3. Add the Logger initialization to each class.
4. Implement the detailed try/catch blocks with contextual logging.
5. Add the health check command.
6. Test with the Python server and verify logs are being generated.

## Sample NLog Configuration

```xml
<?xml version="1.0" encoding="utf-8" ?>
<nlog xmlns="http://www.nlog-project.org/schemas/NLog.xsd"
      xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
    
    <targets>
        <target name="logfile" xsi:type="File"
                fileName="${specialfolder:folder=UserProfile}/scratch/rhinoMcpServer/logs/plugin/plugin_${date:format=yyyy-MM-dd}.log"
                layout="[${longdate}] [${level:uppercase=true}] [plugin] ${message} ${exception:format=toString}" />
        <target name="console" xsi:type="Console"
                layout="[${longdate}] [${level:uppercase=true}] [plugin] ${message} ${exception:format=toString}" />
    </targets>
    
    <rules>
        <logger name="*" minlevel="Debug" writeTo="logfile" />
        <logger name="*" minlevel="Info" writeTo="console" />
    </rules>
</nlog>
```

## Key Areas to Monitor

Based on the error patterns, focus logging on these key areas:

1. **Document State** - Check if RhinoDoc.ActiveDoc is null before attempting operations
2. **Socket Communication** - Log all incoming/outgoing messages
3. **Parameter Validation** - Verify parameters before using them
4. **Geometry Creation** - Add safeguards around geometry creation operations
5. **UI Thread Operations** - Ensure document modifications happen on the UI thread

This enhanced logging will help identify which specific object is null and under what conditions the error occurs. 