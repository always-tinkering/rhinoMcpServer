#!/usr/bin/env python3
"""
RhinoMCP Server - Model Context Protocol server for Rhino 3D

This server provides AI systems with access to Rhino 3D's Python scripting
capabilities through the Model Context Protocol (MCP).
"""

import asyncio
import json
import logging
import sys
from typing import Dict, List, Optional, Any, Tuple

try:
    # Import Rhino-specific modules
    import rhinoscriptsyntax as rs
    import Rhino
    import scriptcontext as sc
    from Rhino.UI import Dialogs
except ImportError:
    # For development/testing outside of Rhino
    print("Warning: Running outside of Rhino environment. Some features will be mocked.")
    class MockRhino:
        class UI:
            class Dialogs:
                @staticmethod
                def ShowMessageBox(message, title, buttons=None, icon=None):
                    print(f"[MOCK] Dialog: {title} - {message}")
                    return True
    Rhino = MockRhino()
    
    def mock_rs_function(*args, **kwargs):
        print(f"[MOCK] Called rhinoscript function with args: {args}, kwargs: {kwargs}")
        return None
    
    class MockRS:
        def __getattr__(self, name):
            return mock_rs_function
    
    rs = MockRS()
    
    class MockSC:
        doc = None
    
    sc = MockSC()

# Import MCP SDK
from mcp.stable import (
    FastMCP,
    Resource,
    ResourceData,
    ResourcePath,
    Tool,
    ToolCall,
    ToolResult,
    UserConsent,
    Status,
)
from pydantic import BaseModel, Field

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("RhinoMCP")

# Models for Rhino objects
class RhinoObjectProperties(BaseModel):
    """Properties of a Rhino object"""
    id: str
    type: str
    layer: str
    name: Optional[str] = None
    color: Optional[str] = None
    position: Optional[Dict[str, float]] = None
    bbox: Optional[Dict[str, Dict[str, float]]] = None

class SceneContext(BaseModel):
    """The current state of the Rhino scene"""
    object_count: int
    objects: List[RhinoObjectProperties]
    active_view: str
    layers: List[str]

class CreateSphereParams(BaseModel):
    """Parameters for creating a sphere"""
    center_x: float = Field(0.0, description="X coordinate of center point")
    center_y: float = Field(0.0, description="Y coordinate of center point")
    center_z: float = Field(0.0, description="Z coordinate of center point")
    radius: float = Field(1.0, description="Radius of the sphere")
    color: Optional[str] = Field(None, description="Color in hex format (e.g. #FF0000)")

class CreateSphereResult(BaseModel):
    """Result of creating a sphere"""
    object_id: str
    properties: RhinoObjectProperties

# Helper functions for Rhino operations
def get_object_properties(obj_id: str) -> RhinoObjectProperties:
    """Extract properties from a Rhino object"""
    try:
        obj_type = rs.ObjectType(obj_id)
        type_name = str(obj_type)
        layer = rs.ObjectLayer(obj_id)
        name = rs.ObjectName(obj_id)
        color_rgb = rs.ObjectColor(obj_id)
        color = f"#{color_rgb[0]:02x}{color_rgb[1]:02x}{color_rgb[2]:02x}" if color_rgb else None
        
        # Get position (centroid)
        centroid = rs.SurfaceVolumeCentroid(obj_id)
        if not centroid and rs.IsCurve(obj_id):
            centroid = rs.CurveAreaCentroid(obj_id)
        if not centroid and rs.IsPoint(obj_id):
            centroid = rs.PointCoordinates(obj_id)
        
        position = None
        if centroid:
            position = {"x": centroid[0], "y": centroid[1], "z": centroid[2]}
        
        # Get bounding box
        bbox_corners = rs.BoundingBox(obj_id)
        bbox = None
        if bbox_corners:
            min_pt, max_pt = bbox_corners[0], bbox_corners[6]
            bbox = {
                "min": {"x": min_pt[0], "y": min_pt[1], "z": min_pt[2]},
                "max": {"x": max_pt[0], "y": max_pt[1], "z": max_pt[2]}
            }
        
        return RhinoObjectProperties(
            id=obj_id,
            type=type_name,
            layer=layer,
            name=name,
            color=color,
            position=position,
            bbox=bbox
        )
    except Exception as e:
        logger.error(f"Error getting object properties for {obj_id}: {e}")
        return RhinoObjectProperties(id=obj_id, type="unknown", layer="unknown")

def get_all_objects() -> List[RhinoObjectProperties]:
    """Get properties for all objects in the document"""
    objects = []
    try:
        all_objects = rs.AllObjects()
        if all_objects:
            for obj_id in all_objects:
                objects.append(get_object_properties(obj_id))
    except Exception as e:
        logger.error(f"Error getting all objects: {e}")
    
    return objects

def create_sphere(params: CreateSphereParams) -> Tuple[str, RhinoObjectProperties]:
    """Create a sphere in Rhino"""
    try:
        center = [params.center_x, params.center_y, params.center_z]
        sphere_id = rs.AddSphere(center, params.radius)
        
        if params.color:
            try:
                # Convert hex color to RGB
                color = params.color.lstrip('#')
                r, g, b = tuple(int(color[i:i+2], 16) for i in (0, 2, 4))
                rs.ObjectColor(sphere_id, (r, g, b))
            except Exception as e:
                logger.warning(f"Failed to set color: {e}")
        
        properties = get_object_properties(sphere_id)
        return sphere_id, properties
    except Exception as e:
        logger.error(f"Error creating sphere: {e}")
        raise

# MCP Server Implementation
class RhinoMCPServer:
    """MCP Server for Rhino integration"""
    
    def __init__(self):
        self.mcp = FastMCP(stdio=True)
        self.register_resources()
        self.register_tools()
        logger.info("RhinoMCP Server initialized")
    
    def register_resources(self):
        """Register resource handlers"""
        
        @self.mcp.resource_handler("scene")
        async def get_scene_info(_: ResourcePath) -> ResourceData:
            """Get information about the current Rhino scene"""
            logger.info("Getting scene information")
            
            try:
                objects = get_all_objects()
                active_view = rs.CurrentView()
                layers = rs.LayerNames()
                
                scene_data = SceneContext(
                    object_count=len(objects),
                    objects=objects,
                    active_view=active_view,
                    layers=layers
                )
                
                return ResourceData(scene_data.model_dump())
            except Exception as e:
                logger.error(f"Error getting scene info: {e}")
                return ResourceData({"error": str(e)})
    
    def register_tools(self):
        """Register tools"""
        
        @self.mcp.tool("create_sphere")
        async def create_sphere_tool(tool_call: ToolCall) -> ToolResult:
            """Create a sphere in the Rhino document"""
            try:
                params = CreateSphereParams(**tool_call.parameters)
                
                # Request user consent
                consent_message = f"An AI agent wants to create a sphere at ({params.center_x}, {params.center_y}, {params.center_z}) with radius {params.radius}."
                if params.color:
                    consent_message += f" Color: {params.color}"
                
                consent = await self.request_user_consent(
                    title="Create Sphere",
                    message=consent_message
                )
                
                if not consent.approved:
                    logger.info("User rejected create sphere operation")
                    return ToolResult(
                        status=Status.DENIED,
                        message="User denied permission to create sphere"
                    )
                
                # Create the sphere
                logger.info(f"Creating sphere with params: {params}")
                sphere_id, properties = create_sphere(params)
                
                result = CreateSphereResult(
                    object_id=sphere_id,
                    properties=properties
                )
                
                return ToolResult(
                    status=Status.SUCCESS,
                    message="Sphere created successfully",
                    data=result.model_dump()
                )
            except Exception as e:
                logger.error(f"Error in create_sphere tool: {e}")
                return ToolResult(
                    status=Status.ERROR,
                    message=f"Failed to create sphere: {str(e)}"
                )
    
    async def request_user_consent(self, title: str, message: str) -> UserConsent:
        """Request consent from the user for an operation"""
        try:
            # Show dialog to user and wait for response
            result = Dialogs.ShowMessageBox(
                message, 
                title,
                buttons=Rhino.UI.ShowMessageButton.YesNo,
                icon=Rhino.UI.ShowMessageIcon.Question
            )
            
            approved = result == Rhino.UI.ShowMessageResult.Yes
            logger.info(f"User consent for '{title}': {approved}")
            
            return UserConsent(
                approved=approved,
                reason=None if approved else "User declined"
            )
        except Exception as e:
            logger.error(f"Error requesting user consent: {e}")
            # Default to not approved on error
            return UserConsent(
                approved=False,
                reason=f"Error showing consent dialog: {str(e)}"
            )
    
    async def run(self):
        """Run the MCP server"""
        logger.info("Starting RhinoMCP Server...")
        await self.mcp.run()

def main():
    """Main entry point"""
    server = RhinoMCPServer()
    asyncio.run(server.run())

if __name__ == "__main__":
    main() 