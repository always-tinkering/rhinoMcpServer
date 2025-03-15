using System;
using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace RhinoMcpPlugin.Models
{
    /// <summary>
    /// Properties of a Rhino object that can be exposed via MCP
    /// </summary>
    public class RhinoObjectProperties
    {
        /// <summary>
        /// The object's unique identifier
        /// </summary>
        [JsonPropertyName("id")]
        public string Id { get; set; }

        /// <summary>
        /// The type of object (e.g., "Curve", "Surface", "Mesh")
        /// </summary>
        [JsonPropertyName("type")]
        public string Type { get; set; }

        /// <summary>
        /// The layer the object is on
        /// </summary>
        [JsonPropertyName("layer")]
        public string Layer { get; set; }

        /// <summary>
        /// The name of the object (if any)
        /// </summary>
        [JsonPropertyName("name")]
        public string Name { get; set; }

        /// <summary>
        /// The color of the object in hex format (e.g., "#FF0000")
        /// </summary>
        [JsonPropertyName("color")]
        public string Color { get; set; }

        /// <summary>
        /// The position (centroid) of the object
        /// </summary>
        [JsonPropertyName("position")]
        public Position Position { get; set; }

        /// <summary>
        /// The bounding box of the object
        /// </summary>
        [JsonPropertyName("bbox")]
        public BoundingBox BoundingBox { get; set; }
    }

    /// <summary>
    /// Represents a 3D position
    /// </summary>
    public class Position
    {
        [JsonPropertyName("x")]
        public double X { get; set; }

        [JsonPropertyName("y")]
        public double Y { get; set; }

        [JsonPropertyName("z")]
        public double Z { get; set; }
    }

    /// <summary>
    /// Represents a bounding box with min and max points
    /// </summary>
    public class BoundingBox
    {
        [JsonPropertyName("min")]
        public Position Min { get; set; }

        [JsonPropertyName("max")]
        public Position Max { get; set; }
    }

    /// <summary>
    /// Represents the current state of the Rhino scene
    /// </summary>
    public class SceneContext
    {
        /// <summary>
        /// The number of objects in the scene
        /// </summary>
        [JsonPropertyName("object_count")]
        public int ObjectCount { get; set; }

        /// <summary>
        /// The objects in the scene
        /// </summary>
        [JsonPropertyName("objects")]
        public List<RhinoObjectProperties> Objects { get; set; }

        /// <summary>
        /// The name of the active view
        /// </summary>
        [JsonPropertyName("active_view")]
        public string ActiveView { get; set; }

        /// <summary>
        /// The layers in the document
        /// </summary>
        [JsonPropertyName("layers")]
        public List<string> Layers { get; set; }
    }
} 