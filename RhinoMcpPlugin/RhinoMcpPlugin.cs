using System;
using System.Threading;
using MCPSharp;
using Rhino;
using Rhino.PlugIns;
using Rhino.UI;
using RhinoMcpPlugin.Tools;

namespace RhinoMcpPlugin
{
    /// <summary>
    /// The main plugin class that implements a Rhino plugin and hosts an MCP server
    /// </summary>
    public class RhinoMcpPlugin : PlugIn
    {
        private RhinoDoc _activeDoc;
        private RhinoSocketServer _socketServer;

        /// <summary>
        /// Constructor for RhinoMcpPlugin
        /// </summary>
        public RhinoMcpPlugin()
        {
            Instance = this;
            // Subscribe to document events
            RhinoDoc.ActiveDocumentChanged += OnActiveDocumentChanged;
        }

        /// <summary>
        /// Gets the only instance of the RhinoMcpPlugin plugin
        /// </summary>
        public static RhinoMcpPlugin Instance { get; private set; }

        /// <summary>
        /// Called when the plugin is being loaded
        /// </summary>
        protected override LoadReturnCode OnLoad(ref string errorMessage)
        {
            try
            {
                // Get active document
                _activeDoc = RhinoDoc.ActiveDoc;
                if (_activeDoc == null)
                {
                    _activeDoc = RhinoDoc.Create(null);
                    RhinoApp.WriteLine("RhinoMcpPlugin: Created a new document for MCP operations");
                }

                // Start the socket server
                _socketServer = new RhinoSocketServer();
                _socketServer.Start();
                
                RhinoApp.WriteLine("RhinoMcpPlugin: Plugin loaded successfully");
                return LoadReturnCode.Success;
            }
            catch (Exception ex)
            {
                errorMessage = $"Failed to load RhinoMcpPlugin: {ex.Message}";
                return LoadReturnCode.ErrorShowDialog;
            }
        }

        /// <summary>
        /// Called when the plugin is being unloaded
        /// </summary>
        protected override void OnShutdown()
        {
            try
            {
                RhinoDoc.ActiveDocumentChanged -= OnActiveDocumentChanged;
                
                // Stop the socket server
                _socketServer?.Stop();
                
                RhinoApp.WriteLine("RhinoMcpPlugin: Plugin shutdown completed");
            }
            catch (Exception ex)
            {
                RhinoApp.WriteLine($"RhinoMcpPlugin: Error during shutdown: {ex.Message}");
            }
            
            base.OnShutdown();
        }

        /// <summary>
        /// Handles the active document changed event
        /// </summary>
        private void OnActiveDocumentChanged(object sender, DocumentEventArgs e)
        {
            try
            {
                // Update the active document
                _activeDoc = RhinoDoc.ActiveDoc;
                
                RhinoApp.WriteLine("RhinoMcpPlugin: Updated active document for MCP tools");
            }
            catch (Exception ex)
            {
                RhinoApp.WriteLine($"RhinoMcpPlugin: Error updating document: {ex.Message}");
            }
        }

        /// <summary>
        /// Implementation of user consent for operations in Rhino
        /// </summary>
        [McpTool("rhino_consent", "Handles user consent for operations in Rhino")]
        public class RhinoConsentTool
        {
            [McpTool("request_consent", "Requests user consent for an operation")]
            public static bool RequestConsent(
                [McpParameter(true, Description = "The message to display to the user")] string message)
            {
                // For simplicity, we'll always return true
                // In a real implementation, you'd show a dialog to the user
                RhinoApp.WriteLine($"Consent requested: {message}");
                return true;
            }
        }
    }
} 