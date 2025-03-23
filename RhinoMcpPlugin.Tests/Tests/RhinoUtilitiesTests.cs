using System;
using System.Drawing;
using NUnit.Framework;
using RhinoMcpPlugin.Tests.Mocks;
using Rhino.Geometry;
using Rhino.DocObjects;
using Moq;

namespace RhinoMcpPlugin.Tests
{
    [TestFixture]
    [Category("Utilities")]
    public class RhinoUtilitiesTests
    {
        private MockRhinoDoc _doc;
        
        [SetUp]
        public void Setup()
        {
            _doc = new MockRhinoDoc();
        }
        
        [Test]
        public void ParseHexColor_ValidHexWithHash_ReturnsCorrectColor()
        {
            // Arrange
            string hexColor = "#FF0000";
            
            // Act
            Color? color = RhinoUtilities.ParseHexColor(hexColor);
            
            // Assert
            Assert.That(color, Is.Not.Null);
            Assert.That(color.Value.R, Is.EqualTo(255));
            Assert.That(color.Value.G, Is.EqualTo(0));
            Assert.That(color.Value.B, Is.EqualTo(0));
        }
        
        [Test]
        public void ParseHexColor_ValidHexWithoutHash_ReturnsCorrectColor()
        {
            // Arrange
            string hexColor = "00FF00";
            
            // Act
            Color? color = RhinoUtilities.ParseHexColor(hexColor);
            
            // Assert
            Assert.That(color, Is.Not.Null);
            Assert.That(color.Value.R, Is.EqualTo(0));
            Assert.That(color.Value.G, Is.EqualTo(255));
            Assert.That(color.Value.B, Is.EqualTo(0));
        }
        
        [Test]
        public void ParseHexColor_ValidHexWithAlpha_ReturnsCorrectColor()
        {
            // Arrange
            string hexColor = "80FF0000";
            
            // Act
            Color? color = RhinoUtilities.ParseHexColor(hexColor);
            
            // Assert
            Assert.That(color, Is.Not.Null);
            Assert.That(color.Value.A, Is.EqualTo(128));
            Assert.That(color.Value.R, Is.EqualTo(255));
            Assert.That(color.Value.G, Is.EqualTo(0));
            Assert.That(color.Value.B, Is.EqualTo(0));
        }
        
        [Test]
        public void ParseHexColor_NamedColor_ReturnsCorrectColor()
        {
            // Arrange
            string colorName = "Red";
            
            // Act
            Color? color = RhinoUtilities.ParseHexColor(colorName);
            
            // Assert
            Assert.That(color, Is.Not.Null);
            Assert.That(color.Value.R, Is.EqualTo(255));
            Assert.That(color.Value.G, Is.EqualTo(0));
            Assert.That(color.Value.B, Is.EqualTo(0));
        }
        
        [Test]
        public void ParseHexColor_InvalidHex_ReturnsNull()
        {
            // Arrange
            string hexColor = "XYZ123";
            
            // Act
            Color? color = RhinoUtilities.ParseHexColor(hexColor);
            
            // Assert
            Assert.That(color, Is.Null);
        }
        
        [Test]
        public void ParseHexColor_EmptyString_ReturnsNull()
        {
            // Arrange
            string hexColor = "";
            
            // Act
            Color? color = RhinoUtilities.ParseHexColor(hexColor);
            
            // Assert
            Assert.That(color, Is.Null);
        }
        
        // The following tests would require more complex mocking to simulate RhinoObject
        // and need to be rewritten when we have access to the actual RhinoUtilities implementation
        
        [Test]
        public void GetObjectProperties_ValidObject_ReturnsCorrectProperties()
        {
            // Arrange
            var sphere = new Sphere(new Point3d(1, 2, 3), 5);
            var sphereObj = _doc.AddSphere(sphere);
            
            // Create a dynamic mock for RhinoObject
            dynamic mockRhinoObject = new MockDynamicRhinoObject(sphereObj, _doc);
            
            // Act
            var props = RhinoUtilities.GetObjectProperties(mockRhinoObject);
            
            // Assert
            Assert.That(props, Is.Not.Null);
            Assert.That(props.Id, Is.EqualTo(sphereObj.Id.ToString()));
            Assert.That(props.Type, Is.EqualTo("None")); // Our mock returns ObjectType.None
            Assert.That(props.Layer, Is.EqualTo("Default"));
            Assert.That(props.Position.X, Is.EqualTo(1).Within(0.001));
            Assert.That(props.Position.Y, Is.EqualTo(2).Within(0.001));
            Assert.That(props.Position.Z, Is.EqualTo(3).Within(0.001));
        }
        
        [Test]
        public void GetObjectProperties_NullObject_ReturnsNull()
        {
            // Act
            var properties = RhinoUtilities.GetObjectProperties(null);
            
            // Assert
            Assert.That(properties, Is.Null);
        }
        
        [Test]
        public void GetAllObjects_DocWithObjects_ReturnsAllObjects()
        {
            // Arrange
            var sphere = new Sphere(new Point3d(1, 2, 3), 5);
            var box = new Box(new BoundingBox(new Point3d(0, 0, 0), new Point3d(10, 10, 10)));
            _doc.AddSphere(sphere);
            _doc.AddBox(box);
            
            // Act
            // Create a dynamic mock for RhinoDoc to use with the static utility method
            dynamic mockRhinoDoc = new MockDynamicRhinoDoc(_doc);
            var objects = RhinoUtilities.GetAllObjects(mockRhinoDoc);
            
            // Assert
            Assert.That(objects, Is.Not.Null);
            Assert.That(objects.Count, Is.EqualTo(2));
        }
        
        [Test]
        public void GetAllObjects_NullDoc_ReturnsEmptyList()
        {
            // Act
            var objects = RhinoUtilities.GetAllObjects(null);
            
            // Assert
            Assert.That(objects, Is.Not.Null);
            Assert.That(objects.Count, Is.EqualTo(0));
        }
        
        [Test]
        public void GetSceneContext_ValidDoc_ReturnsSceneInfo()
        {
            // Arrange
            // Create test objects
            var sphere = new Sphere(new Point3d(1, 2, 3), 5);
            var box = new Box(new BoundingBox(new Point3d(0, 0, 0), new Point3d(10, 10, 10)));
            
            // Add test objects to mock doc
            var sphereObj = _doc.AddSphere(sphere);
            var boxObj = _doc.AddBox(box);

            // Add a test layer
            _doc.AddLayer("TestLayer", Color.Blue);
            
            // Create a dynamic mock for RhinoDoc to use with the static utility method
            dynamic mockRhinoDoc = new MockDynamicRhinoDoc(_doc);
            
            // Act
            var sceneContext = RhinoUtilities.GetSceneContext(mockRhinoDoc);
            
            // Assert
            Assert.That(sceneContext, Is.Not.Null);
            Assert.That(sceneContext.ObjectCount, Is.EqualTo(2));
            Assert.That(sceneContext.Objects, Has.Count.EqualTo(2));
            Assert.That(sceneContext.ActiveView, Is.EqualTo("None"));
            Assert.That(sceneContext.Layers, Has.Count.EqualTo(2));
            Assert.That(sceneContext.Layers, Contains.Item("Default"));
            Assert.That(sceneContext.Layers, Contains.Item("TestLayer"));
        }
        
        [Test]
        public void GetSceneContext_NullDoc_ThrowsArgumentNullException()
        {
            // Assert
            Assert.Throws<ArgumentNullException>(() => RhinoUtilities.GetSceneContext(null));
        }
    }

    /// <summary>
    /// A dynamic proxy to help with RhinoDoc mocking
    /// </summary>
    public class MockDynamicRhinoDoc : System.Dynamic.DynamicObject
    {
        private readonly MockRhinoDoc _mockDoc;
        private readonly MockRhinoViews _views = new MockRhinoViews();

        public MockDynamicRhinoDoc(MockRhinoDoc mockDoc)
        {
            _mockDoc = mockDoc;
        }
        
        // Passthrough to mock object table
        public MockRhinoObjectTable Objects => (MockRhinoObjectTable)_mockDoc.Objects;
        
        // Passthrough to mock layer table
        public MockLayerTable Layers => (MockLayerTable)_mockDoc.Layers;
        
        // Provide a views collection
        public MockRhinoViews Views => _views;
    }

    /// <summary>
    /// A dynamic proxy to help with RhinoObject mocking
    /// </summary>
    public class MockDynamicRhinoObject : System.Dynamic.DynamicObject
    {
        private readonly IMockRhinoObject _mockObject;
        private readonly MockRhinoDoc _mockDoc;

        public MockDynamicRhinoObject(IMockRhinoObject mockObject, MockRhinoDoc mockDoc)
        {
            _mockObject = mockObject;
            _mockDoc = mockDoc;
        }
        
        // Pass through for Id
        public Guid Id => _mockObject.Id;
        
        // Pass through for Attributes
        public IMockObjectAttributes Attributes => _mockObject.Attributes;
        
        // Pass through for Geometry
        public GeometryBase Geometry => _mockObject.Geometry;
        
        // Pass through for ObjectType
        public ObjectType ObjectType => _mockObject.ObjectType;
        
        // Provide document reference
        public dynamic Document => new MockDynamicRhinoDoc(_mockDoc);
        
        // Make sure we can serialize this object
        public override string ToString() => $"MockRhinoObject:{Id}";
    }

    /// <summary>
    /// Mock for Rhino views collection
    /// </summary>
    public class MockRhinoViews
    {
        private readonly MockRhinoView _activeView = new MockRhinoView();
        
        public MockRhinoView ActiveView => _activeView;
    }

    /// <summary>
    /// Mock for a Rhino view
    /// </summary>
    public class MockRhinoView
    {
        private readonly MockViewport _activeViewport = new MockViewport("Perspective");
        
        public MockViewport ActiveViewport => _activeViewport;
    }

    /// <summary>
    /// Mock for a Rhino viewport
    /// </summary>
    public class MockViewport
    {
        public string Name { get; }
        
        public MockViewport(string name)
        {
            Name = name;
        }
    }
} 