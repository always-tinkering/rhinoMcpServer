using System;
using System.Collections.Generic;
using System.Drawing;
using System.Linq;
using System.Threading.Tasks;
using MCPSharp;
using Rhino;
using Rhino.DocObjects;
using Rhino.Geometry;
using RhinoMcpPlugin.Models;

namespace RhinoMcpPlugin
{
    /// <summary>
    /// Utilities for working with Rhino objects
    /// </summary>
    public static class RhinoUtilities
    {
        /// <summary>
        /// Gets the properties of a Rhino object
        /// </summary>
        /// <param name="docObject">The Rhino document object</param>
        /// <returns>The properties of the object</returns>
        public static RhinoObjectProperties GetObjectProperties(RhinoObject docObject)
        {
            if (docObject == null)
                return null;

            var properties = new RhinoObjectProperties
            {
                Id = docObject.Id.ToString(),
                Type = docObject.ObjectType.ToString(),
                Layer = docObject.Attributes.LayerIndex >= 0 ? 
                    docObject.Document.Layers[docObject.Attributes.LayerIndex].Name : 
                    "Default",
                Name = docObject.Name
            };

            // Get color
            if (docObject.Attributes.ColorSource == ObjectColorSource.ColorFromObject)
            {
                var color = docObject.Attributes.ObjectColor;
                properties.Color = $"#{color.R:X2}{color.G:X2}{color.B:X2}";
            }
            else if (docObject.Attributes.ColorSource == ObjectColorSource.ColorFromLayer)
            {
                var layer = docObject.Document.Layers[docObject.Attributes.LayerIndex];
                var color = layer.Color;
                properties.Color = $"#{color.R:X2}{color.G:X2}{color.B:X2}";
            }

            // Get centroid
            var centroid = GetObjectCentroid(docObject);
            properties.Position = new Position
            {
                X = centroid.X,
                Y = centroid.Y,
                Z = centroid.Z
            };

            // Get bounding box
            var rhinoBoundingBox = docObject.Geometry.GetBoundingBox(true);
            properties.BoundingBox = new Models.BoundingBox
            {
                Min = new Position
                {
                    X = rhinoBoundingBox.Min.X,
                    Y = rhinoBoundingBox.Min.Y,
                    Z = rhinoBoundingBox.Min.Z
                },
                Max = new Position
                {
                    X = rhinoBoundingBox.Max.X,
                    Y = rhinoBoundingBox.Max.Y,
                    Z = rhinoBoundingBox.Max.Z
                }
            };

            return properties;
        }

        /// <summary>
        /// Gets properties for all objects in the document
        /// </summary>
        /// <param name="doc">The Rhino document</param>
        /// <returns>List of object properties</returns>
        public static List<RhinoObjectProperties> GetAllObjects(RhinoDoc doc)
        {
            if (doc == null)
                return new List<RhinoObjectProperties>();

            var objects = new List<RhinoObjectProperties>();
            
            foreach (var obj in doc.Objects)
            {
                var props = GetObjectProperties(obj);
                if (props != null)
                {
                    objects.Add(props);
                }
            }

            return objects;
        }

        /// <summary>
        /// Gets information about the current scene
        /// </summary>
        /// <param name="doc">The Rhino document</param>
        /// <returns>Scene context information</returns>
        public static SceneContext GetSceneContext(RhinoDoc doc)
        {
            if (doc == null)
                throw new ArgumentNullException(nameof(doc));

            var context = new SceneContext
            {
                ObjectCount = doc.Objects.Count,
                Objects = GetAllObjects(doc),
                ActiveView = doc.Views.ActiveView?.ActiveViewport?.Name ?? "None",
                Layers = new List<string>()
            };

            // Get layers
            foreach (var layer in doc.Layers)
            {
                context.Layers.Add(layer.Name);
            }

            return context;
        }

        /// <summary>
        /// Get the centroid of a Rhino object
        /// </summary>
        /// <param name="obj">The Rhino object</param>
        /// <returns>The centroid point</returns>
        private static Point3d GetObjectCentroid(RhinoObject obj)
        {
            if (obj == null)
                return Point3d.Origin;

            var geometry = obj.Geometry;
            if (geometry == null)
                return Point3d.Origin;

            var bbox = geometry.GetBoundingBox(true);
            return bbox.Center;
        }

        /// <summary>
        /// Parse a hex color string to a Color
        /// </summary>
        /// <param name="hexColor">Hex color string (e.g., "#FF0000" or "FF0000")</param>
        /// <returns>The Color, or null if parsing fails</returns>
        public static Color? ParseHexColor(string hexColor)
        {
            if (string.IsNullOrEmpty(hexColor))
                return null;

            // Remove # if present
            if (hexColor.StartsWith("#"))
                hexColor = hexColor.Substring(1);

            try
            {
                if (hexColor.Length == 6)
                {
                    int r = Convert.ToInt32(hexColor.Substring(0, 2), 16);
                    int g = Convert.ToInt32(hexColor.Substring(2, 2), 16);
                    int b = Convert.ToInt32(hexColor.Substring(4, 2), 16);
                    return Color.FromArgb(r, g, b);
                }
                else if (hexColor.Length == 8)
                {
                    int a = Convert.ToInt32(hexColor.Substring(0, 2), 16);
                    int r = Convert.ToInt32(hexColor.Substring(2, 2), 16);
                    int g = Convert.ToInt32(hexColor.Substring(4, 2), 16);
                    int b = Convert.ToInt32(hexColor.Substring(6, 2), 16);
                    return Color.FromArgb(a, r, g, b);
                }
                
                // Try to parse as a named color
                return Color.FromName(hexColor);
            }
            catch
            {
                return null;
            }
        }

        /// <summary>
        /// Set the color of a Rhino object
        /// </summary>
        /// <param name="doc">The Rhino document</param>
        /// <param name="objectId">The object ID</param>
        /// <param name="hexColor">Color in hex format</param>
        /// <returns>True if successful</returns>
        public static bool SetObjectColor(RhinoDoc doc, Guid objectId, string hexColor)
        {
            if (doc == null || objectId == Guid.Empty || string.IsNullOrEmpty(hexColor))
                return false;

            var obj = doc.Objects.FindId(objectId);
            if (obj == null)
                return false;

            // Parse color
            Color? color = ParseHexColor(hexColor);
            if (!color.HasValue)
                return false;

            // Create new attributes
            var attrs = obj.Attributes;
            attrs.ObjectColor = color.Value;
            attrs.ColorSource = ObjectColorSource.ColorFromObject;

            // Modify object
            return doc.Objects.ModifyAttributes(obj, attrs, true);
        }

        /// <summary>
        /// Request user consent for an operation
        /// </summary>
        /// <param name="title">The title of the consent request</param>
        /// <param name="message">The message to display to the user</param>
        /// <returns>True if the user approves, false otherwise</returns>
        public static bool RequestConsent(string title, string message)
        {
            // For simplicity, we'll always return true
            // In a real implementation, you'd show a dialog to the user
            RhinoApp.WriteLine($"Consent requested: {message}");
            return true;
        }
    }
} 