using System;
using System.Reflection;
using NUnit.Framework;
using Moq;
using RhinoMcpPlugin.Tests.Mocks;
using Rhino;
using Rhino.PlugIns;

namespace RhinoMcpPlugin.Tests
{
    [TestFixture]
    [Category("Plugin")]
    public class RhinoMcpPluginTests
    {
        private global::RhinoMcpPlugin.RhinoMcpPlugin _plugin;
        
        [SetUp]
        public void Setup()
        {
            // Create a mock RhinoDoc that will be used during testing
            new MockRhinoDoc();
            
            // Create plugin instance
            _plugin = new global::RhinoMcpPlugin.RhinoMcpPlugin();
        }
        
        [Test]
        public void Constructor_WhenCalled_SetsInstanceProperty()
        {
            // Assert
            Assert.That(global::RhinoMcpPlugin.RhinoMcpPlugin.Instance, Is.EqualTo(_plugin));
        }
        
        // The following tests would require more sophisticated mocking of the Rhino environment
        // We'll implement simplified versions focusing on basic plugin functionality
        
        /*
        [Test]
        public void OnLoad_WhenCalled_StartsSocketServer()
        {
            // This test would need to be adapted based on how the RhinoMcpPlugin 
            // interacts with RhinoDoc and how it initializes the socket server
        }
        
        [Test]
        public void OnShutdown_AfterOnLoad_StopsSocketServer()
        {
            // This test would need to be adapted based on how the RhinoMcpPlugin 
            // manages its resources and shuts down the socket server
        }
        
        [Test]
        public void OnActiveDocumentChanged_WhenCalled_UpdatesActiveDoc()
        {
            // This test would need to be adapted based on how the RhinoMcpPlugin
            // handles document change events
        }
        */
        
        [Test]
        public void RhinoConsentTool_RequestConsent_ReturnsTrue()
        {
            // Act
            var result = global::RhinoMcpPlugin.RhinoMcpPlugin.RhinoConsentTool.RequestConsent("Test consent message");
            
            // Assert
            Assert.That(result, Is.True);
        }
    }
} 