using System;
using System.Net.Sockets;
using System.Text;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using NUnit.Framework;
using RhinoMcpPlugin.Tests.Mocks;

namespace RhinoMcpPlugin.Tests
{
    [TestFixture]
    [Category("SocketServer")]
    public class RhinoSocketServerTests
    {
        private global::RhinoMcpPlugin.RhinoSocketServer _server;
        private int _testPort = 9877; // Use a different port than default for testing
        
        [SetUp]
        public void Setup()
        {
            _server = new global::RhinoMcpPlugin.RhinoSocketServer(_testPort);
        }
        
        [TearDown]
        public void TearDown()
        {
            _server.Stop();
        }
        
        [Test]
        public void Start_WhenCalled_ServerStarts()
        {
            // Arrange - setup is done in the Setup method
            
            // Act
            _server.Start();
            
            // Wait a bit for the server to start
            Thread.Sleep(100);
            
            // Assert - we'll verify the server is running by attempting to connect
            using (var client = new TcpClient())
            {
                try
                {
                    client.Connect("localhost", _testPort);
                    Assert.That(client.Connected, Is.True, "Should be able to connect to the server");
                }
                catch (SocketException ex)
                {
                    Assert.Fail($"Failed to connect to the server: {ex.Message}");
                }
            }
        }
        
        [Test]
        public void Stop_AfterStarting_ServerStops()
        {
            // Arrange
            _server.Start();
            Thread.Sleep(100); // Wait for server to start
            
            // Act
            _server.Stop();
            Thread.Sleep(100); // Wait for server to stop
            
            // Assert - server should no longer accept connections
            using (var client = new TcpClient())
            {
                var ex = Assert.Throws<SocketException>(() => client.Connect("localhost", _testPort));
                Assert.That(ex.SocketErrorCode, Is.EqualTo(SocketError.ConnectionRefused).Or.EqualTo(SocketError.TimedOut));
            }
        }
        
        // The following tests would need adjustments to work with the actual implementation
        // We'll comment them out for now
        
        /*
        [Test]
        public async Task HandleClient_ValidCreateSphereCommand_ReturnsSuccessResponse()
        {
            // This test needs to be adapted based on the actual RhinoSocketServer implementation
            // and how it interacts with the mock RhinoDoc
        }
        
        [Test]
        public async Task HandleClient_MissingRequiredParameter_ReturnsErrorResponse()
        {
            // This test needs to be adapted based on the actual RhinoSocketServer implementation
            // and how it validates parameters
        }
        
        [Test]
        public async Task HandleClient_InvalidCommandType_ReturnsErrorResponse()
        {
            // This test needs to be adapted based on the actual RhinoSocketServer implementation
            // and how it handles unknown commands
        }
        */
    }
} 