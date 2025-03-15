using System;
using Rhino;
using Rhino.Commands;
using Rhino.UI;

namespace RhinoMcpPlugin
{
    /// <summary>
    /// A Rhino command to control the MCP server
    /// </summary>
    public class RhinoMcpCommand : Command
    {
        /// <summary>
        /// Constructor for RhinoMcpCommand
        /// </summary>
        public RhinoMcpCommand()
        {
            Instance = this;
        }

        /// <summary>
        /// The only instance of the RhinoMcpCommand command
        /// </summary>
        public static RhinoMcpCommand Instance { get; private set; }

        /// <summary>
        /// The command name as it appears on the Rhino command line
        /// </summary>
        public override string EnglishName => "RhinoMCP";

        /// <summary>
        /// Called when the user runs the command
        /// </summary>
        protected override Result RunCommand(RhinoDoc doc, RunMode mode)
        {
            // Display a dialog with information about the MCP server
            Dialogs.ShowMessage(
                "RhinoMCP Plugin\n\n" +
                "This plugin hosts an MCP server that allows AI systems to create and manipulate 3D models in Rhino.\n\n" +
                "To use this plugin with Claude Desktop:\n" +
                "1. Make sure Rhino is running with this plugin loaded\n" +
                "2. Configure Claude Desktop to use this MCP server\n" +
                "3. Start interacting with Claude to create 3D models\n\n" +
                "All operations from AI systems will require your explicit consent.",
                "RhinoMCP Plugin"
            );

            return Result.Success;
        }
    }
} 