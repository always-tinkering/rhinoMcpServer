using System;
using System.Collections.Generic;
using System.Text.Json;
using MCPSharp;
using Rhino;
using RhinoMcpPlugin.Models;
using Rhino.DocObjects;

namespace RhinoMcpPlugin.Tools
{
    /// <summary>
    /// MCP tools for managing the Rhino scene
    /// </summary>
    [McpTool("scene_tools", "Tools for managing the Rhino scene")]
    public static class SceneTools
    {
        /// <summary>
        /// Gets information about objects in the current Rhino document
        /// </summary>
        [McpTool("get_scene_info", "Gets information about objects in the current scene")]
        public static Dictionary<string, object> GetSceneInfo()
        {
            try
            {
                // Get the active document
                var doc = RhinoDoc.ActiveDoc;
                if (doc == null)
                {
                    return new Dictionary<string, object>
                    {
                        ["error"] = "No active document found"
                    };
                }

                // Count objects by type
                var countsByType = new Dictionary<string, int>();
                var allObjects = doc.Objects;
                foreach (var obj in allObjects)
                {
                    var typeName = obj.ObjectType.ToString();
                    if (countsByType.ContainsKey(typeName))
                    {
                        countsByType[typeName]++;
                    }
                    else
                    {
                        countsByType[typeName] = 1;
                    }
                }

                // Get layer information
                var layers = new List<object>();
                foreach (var layer in doc.Layers)
                {
                    layers.Add(new
                    {
                        name = layer.Name,
                        visible = layer.IsVisible,
                        locked = layer.IsLocked
                    });
                }

                return new Dictionary<string, object>
                {
                    ["objectCount"] = allObjects.Count,
                    ["objectsByType"] = countsByType,
                    ["layers"] = layers
                };
            }
            catch (Exception ex)
            {
                return new Dictionary<string, object>
                {
                    ["error"] = $"Error getting scene info: {ex.Message}"
                };
            }
        }

        /// <summary>
        /// Clears the current scene by deleting all objects
        /// </summary>
        [McpTool("clear_scene", "Clears all objects from the current scene")]
        public static string ClearScene(
            [McpParameter(Description = "If true, only delete objects on the current layer")] bool currentLayerOnly = false)
        {
            try
            {
                // Get the active document
                var doc = RhinoDoc.ActiveDoc;
                if (doc == null)
                {
                    return "No active document found";
                }

                int deletedCount = 0;

                if (currentLayerOnly)
                {
                    // Get the current layer index
                    int currentLayerIndex = doc.Layers.CurrentLayerIndex;
                    
                    // Delete only objects on the current layer
                    var idsToDelete = new List<Guid>();
                    foreach (var obj in doc.Objects)
                    {
                        if (obj.Attributes.LayerIndex == currentLayerIndex)
                        {
                            idsToDelete.Add(obj.Id);
                        }
                    }
                    
                    // Delete the collected objects
                    foreach (var id in idsToDelete)
                    {
                        if (doc.Objects.Delete(id, true))
                        {
                            deletedCount++;
                        }
                    }
                }
                else
                {
                    // Delete all objects
                    doc.Objects.Clear();
                    deletedCount = doc.Objects.Count;
                }

                // Update views
                doc.Views.Redraw();
                
                return $"Cleared scene: {deletedCount} objects deleted";
            }
            catch (Exception ex)
            {
                return $"Error clearing scene: {ex.Message}";
            }
        }

        /// <summary>
        /// Creates a new layer in the document
        /// </summary>
        [McpTool("create_layer", "Creates a new layer in the Rhino document")]
        public static string CreateLayer(
            [McpParameter(true, Description = "Name of the new layer")] string name,
            [McpParameter(Description = "Optional color for the layer (e.g., 'red', 'blue', etc.)")] string color = null)
        {
            try
            {
                // Get the active document
                var doc = RhinoDoc.ActiveDoc;
                if (doc == null)
                {
                    return "No active document found";
                }

                // Check if layer with this name already exists
                var existingLayerIndex = doc.Layers.FindByFullPath(name, -1);
                if (existingLayerIndex >= 0)
                {
                    return $"Layer with name '{name}' already exists";
                }

                // Create new layer
                var layer = new Layer();
                layer.Name = name;
                
                // Set color if specified
                if (!string.IsNullOrEmpty(color))
                {
                    try
                    {
                        var systemColor = System.Drawing.Color.FromName(color);
                        if (systemColor.A > 0)
                        {
                            layer.Color = systemColor;
                        }
                    }
                    catch
                    {
                        // Ignore color parsing errors
                    }
                }

                // Add the layer to the document
                var index = doc.Layers.Add(layer);
                if (index < 0)
                {
                    return "Failed to create layer";
                }

                // Update views
                doc.Views.Redraw();
                
                return $"Created layer '{name}' with index {index}";
            }
            catch (Exception ex)
            {
                return $"Error creating layer: {ex.Message}";
            }
        }
    }
} 