using System;
using System.Collections.Generic;
using System.Text.Json;
using System.Threading.Tasks;
using MCPSharp;
using Rhino;
using Rhino.Geometry;
using RhinoMcpPlugin.Models;
using Rhino.DocObjects;

namespace RhinoMcpPlugin.Tools
{
    /// <summary>
    /// MCP tools for creating basic geometric shapes in Rhino
    /// </summary>
    [McpTool("geometry_tools", "Tools for creating and manipulating geometric objects in Rhino")]
    public static class GeometryTools
    {
        /// <summary>
        /// Creates a sphere in the Rhino document
        /// </summary>
        [McpTool("create_sphere", "Creates a sphere with the specified center and radius")]
        public static string CreateSphere(
            [McpParameter(true, Description = "X coordinate of the sphere center")] double centerX,
            [McpParameter(true, Description = "Y coordinate of the sphere center")] double centerY,
            [McpParameter(true, Description = "Z coordinate of the sphere center")] double centerZ,
            [McpParameter(true, Description = "Radius of the sphere")] double radius,
            [McpParameter(Description = "Optional color for the sphere (e.g., 'red', 'blue', etc.)")] string color = null)
        {
            try
            {
                // Get the active document
                var doc = RhinoDoc.ActiveDoc;
                if (doc == null)
                {
                    return "No active document found";
                }

                // Create the sphere
                var center = new Point3d(centerX, centerY, centerZ);
                var sphere = new Sphere(center, radius);

                // Add the sphere to the document
                var attributes = new ObjectAttributes();
                if (!string.IsNullOrEmpty(color))
                {
                    // Try to parse the color
                    try
                    {
                        var systemColor = System.Drawing.Color.FromName(color);
                        if (systemColor.A > 0)
                        {
                            attributes.ColorSource = ObjectColorSource.ColorFromObject;
                            attributes.ObjectColor = System.Drawing.Color.FromName(color);
                        }
                    }
                    catch
                    {
                        // Ignore color parsing errors
                    }
                }

                var id = doc.Objects.AddSphere(sphere, attributes);
                
                // Update views
                doc.Views.Redraw();
                
                return $"Created sphere with ID: {id}";
            }
            catch (Exception ex)
            {
                return $"Error creating sphere: {ex.Message}";
            }
        }

        /// <summary>
        /// Creates a box in the Rhino document
        /// </summary>
        [McpTool("create_box", "Creates a box with the specified dimensions")]
        public static string CreateBox(
            [McpParameter(true, Description = "X coordinate of the box corner")] double cornerX,
            [McpParameter(true, Description = "Y coordinate of the box corner")] double cornerY,
            [McpParameter(true, Description = "Z coordinate of the box corner")] double cornerZ,
            [McpParameter(true, Description = "Width of the box (X dimension)")] double width,
            [McpParameter(true, Description = "Depth of the box (Y dimension)")] double depth,
            [McpParameter(true, Description = "Height of the box (Z dimension)")] double height,
            [McpParameter(Description = "Optional color for the box (e.g., 'red', 'blue', etc.)")] string color = null)
        {
            try
            {
                // Get the active document
                var doc = RhinoDoc.ActiveDoc;
                if (doc == null)
                {
                    return "No active document found";
                }

                // Create the box
                var corner = new Point3d(cornerX, cornerY, cornerZ);
                var box = new Box(
                    new Rhino.Geometry.BoundingBox(
                        corner,
                        new Point3d(corner.X + width, corner.Y + depth, corner.Z + height)
                    )
                );

                // Add the box to the document
                var attributes = new ObjectAttributes();
                if (!string.IsNullOrEmpty(color))
                {
                    // Try to parse the color
                    try
                    {
                        var systemColor = System.Drawing.Color.FromName(color);
                        if (systemColor.A > 0)
                        {
                            attributes.ColorSource = ObjectColorSource.ColorFromObject;
                            attributes.ObjectColor = System.Drawing.Color.FromName(color);
                        }
                    }
                    catch
                    {
                        // Ignore color parsing errors
                    }
                }

                var id = doc.Objects.AddBox(box, attributes);
                
                // Update views
                doc.Views.Redraw();
                
                return $"Created box with ID: {id}";
            }
            catch (Exception ex)
            {
                return $"Error creating box: {ex.Message}";
            }
        }
        
        /// <summary>
        /// Creates a cylinder in the Rhino document
        /// </summary>
        [McpTool("create_cylinder", "Creates a cylinder with the specified base point, height, and radius")]
        public static string CreateCylinder(
            [McpParameter(true, Description = "X coordinate of the cylinder base point")] double baseX,
            [McpParameter(true, Description = "Y coordinate of the cylinder base point")] double baseY,
            [McpParameter(true, Description = "Z coordinate of the cylinder base point")] double baseZ,
            [McpParameter(true, Description = "Height of the cylinder")] double height,
            [McpParameter(true, Description = "Radius of the cylinder")] double radius,
            [McpParameter(Description = "Optional color for the cylinder (e.g., 'red', 'blue', etc.)")] string color = null)
        {
            try
            {
                // Get the active document
                var doc = RhinoDoc.ActiveDoc;
                if (doc == null)
                {
                    return "No active document found";
                }

                // Create the cylinder
                var basePoint = new Point3d(baseX, baseY, baseZ);
                var plane = new Plane(basePoint, Vector3d.ZAxis);
                var circle = new Circle(plane, radius);
                var cylinder = new Cylinder(circle, height);

                // Add the cylinder to the document
                var attributes = new ObjectAttributes();
                if (!string.IsNullOrEmpty(color))
                {
                    // Try to parse the color
                    try
                    {
                        var systemColor = System.Drawing.Color.FromName(color);
                        if (systemColor.A > 0)
                        {
                            attributes.ColorSource = ObjectColorSource.ColorFromObject;
                            attributes.ObjectColor = System.Drawing.Color.FromName(color);
                        }
                    }
                    catch
                    {
                        // Ignore color parsing errors
                    }
                }

                var brep = cylinder.ToBrep(true, true);
                var id = doc.Objects.AddBrep(brep, attributes);
                
                // Update views
                doc.Views.Redraw();
                
                return $"Created cylinder with ID: {id}";
            }
            catch (Exception ex)
            {
                return $"Error creating cylinder: {ex.Message}";
            }
        }
    }
} 