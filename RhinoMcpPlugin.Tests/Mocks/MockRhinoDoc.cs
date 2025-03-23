using System;
using System.Collections.Generic;
using System.Drawing;
using Rhino;
using Rhino.DocObjects;
using Rhino.Geometry;

namespace RhinoMcpPlugin.Tests.Mocks
{
    /// <summary>
    /// Interfaces for the mock implementations to make testing easier
    /// </summary>
    public interface IRhinoDocWrapper
    {
        IRhinoObjectTableWrapper Objects { get; }
        ILayerTableWrapper Layers { get; }
        IMockRhinoObject AddSphere(Sphere sphere);
        IMockRhinoObject AddBox(Box box);
        IMockRhinoObject AddCylinder(Cylinder cylinder);
        int AddLayer(string name, Color color);
        bool DeleteObjects(IEnumerable<Guid> objectIds);
        IMockRhinoObject? FindId(Guid id);
    }

    public interface IRhinoObjectTableWrapper
    {
        int Count { get; }
        IEnumerable<IMockRhinoObject> GetAll();
        bool Delete(IMockRhinoObject? obj);
        bool DeleteAll();
        IMockRhinoObject? FindId(Guid id);
        bool ModifyAttributes(IMockRhinoObject obj, IMockObjectAttributes attributes);
    }

    public interface ILayerTableWrapper
    {
        int Count { get; }
        IMockLayer this[int index] { get; }
        IEnumerable<IMockLayer> GetAll();
        int Add(IMockLayer layer);
    }

    public interface IMockRhinoObject
    {
        Guid Id { get; }
        IMockObjectAttributes Attributes { get; set; }
        GeometryBase? Geometry { get; }
        ObjectType ObjectType { get; }
    }

    public interface IMockLayer
    {
        string Name { get; set; }
        Color Color { get; set; }
    }

    public interface IMockObjectAttributes
    {
        Color ObjectColor { get; set; }
        int LayerIndex { get; set; }
        ObjectColorSource ColorSource { get; set; }
    }

    /// <summary>
    /// A mock implementation of RhinoDoc for testing purposes using the wrapper pattern
    /// </summary>
    public class MockRhinoDoc : IRhinoDocWrapper
    {
        private static MockRhinoDoc? _activeDoc;
        private readonly List<MockRhinoObject> _objects = new List<MockRhinoObject>();
        private readonly List<MockLayer> _layers = new List<MockLayer>();
        private readonly MockRhinoObjectTable _objectTable;
        private readonly MockLayerTable _layerTable;

        public MockRhinoDoc()
        {
            _objectTable = new MockRhinoObjectTable(_objects);
            _layerTable = new MockLayerTable(_layers);

            // Create a default layer
            var defaultLayer = new MockLayer("Default", Color.White);
            _layers.Add(defaultLayer);
            
            // Set as active doc
            _activeDoc = this;
        }

        public IRhinoObjectTableWrapper Objects => _objectTable;

        public ILayerTableWrapper Layers => _layerTable;

        public IMockRhinoObject AddSphere(Sphere sphere)
        {
            var mockObj = new MockRhinoObject(sphere.ToBrep()); // Convert to Brep which inherits from GeometryBase
            _objects.Add(mockObj);
            return mockObj;
        }

        public IMockRhinoObject AddBox(Box box)
        {
            var mockObj = new MockRhinoObject(box.ToBrep()); // Convert to Brep which inherits from GeometryBase
            _objects.Add(mockObj);
            return mockObj;
        }

        public IMockRhinoObject AddCylinder(Cylinder cylinder)
        {
            var mockObj = new MockRhinoObject(cylinder.ToBrep(true, true)); // Convert to Brep with cap top and bottom
            _objects.Add(mockObj);
            return mockObj;
        }

        public int AddLayer(string name, Color color)
        {
            var layer = new MockLayer(name, color);
            _layers.Add(layer);
            return _layers.Count - 1;
        }

        public bool DeleteObjects(IEnumerable<Guid> objectIds)
        {
            var deleted = false;
            foreach (var id in objectIds)
            {
                var obj = _objects.Find(o => o.Id == id);
                if (obj != null)
                {
                    _objects.Remove(obj);
                    deleted = true;
                }
            }
            return deleted;
        }

        public IMockRhinoObject? FindId(Guid id)
        {
            return _objects.Find(o => o.Id == id);
        }
        
        public static MockRhinoDoc? ActiveDoc => _activeDoc;
    }
    
    public class MockRhinoObjectTable : IRhinoObjectTableWrapper
    {
        private readonly List<MockRhinoObject> _objects;
        
        public MockRhinoObjectTable(List<MockRhinoObject> objects)
        {
            _objects = objects ?? new List<MockRhinoObject>();
        }
        
        public int Count => _objects.Count;
        
        public IEnumerable<IMockRhinoObject> GetAll()
        {
            return _objects;
        }
        
        public bool Delete(IMockRhinoObject? obj)
        {
            var mockObj = obj as MockRhinoObject;
            if (mockObj != null)
            {
                return _objects.Remove(mockObj);
            }
            return false;
        }
        
        public bool DeleteAll()
        {
            _objects.Clear();
            return true;
        }
        
        public IMockRhinoObject? FindId(Guid id)
        {
            return _objects.Find(o => o.Id == id);
        }
        
        public bool ModifyAttributes(IMockRhinoObject obj, IMockObjectAttributes attributes)
        {
            var mockObj = obj as MockRhinoObject;
            if (mockObj != null)
            {
                mockObj.Attributes = attributes as MockObjectAttributes;
                return true;
            }
            return false;
        }
    }
    
    public class MockLayerTable : ILayerTableWrapper
    {
        private readonly List<MockLayer> _layers;
        
        public MockLayerTable(List<MockLayer> layers)
        {
            _layers = layers;
        }
        
        public int Count => _layers.Count;
        
        public IMockLayer this[int index] => _layers[index];
        
        public IEnumerable<IMockLayer> GetAll()
        {
            return _layers;
        }
        
        public int Add(IMockLayer layer)
        {
            var mockLayer = layer as MockLayer;
            if (mockLayer != null)
            {
                _layers.Add(mockLayer);
                return _layers.Count - 1;
            }
            return -1;
        }
    }
    
    public class MockLayer : IMockLayer
    {
        public string Name { get; set; }
        public Color Color { get; set; }
        
        public MockLayer(string name, Color color)
        {
            Name = name;
            Color = color;
        }
    }
    
    public class MockRhinoObject : IMockRhinoObject
    {
        private readonly Guid _id = Guid.NewGuid();
        private MockObjectAttributes _attributes = new MockObjectAttributes();
        private GeometryBase _geometry;
        
        public MockRhinoObject(GeometryBase geometry)
        {
            _geometry = geometry;
        }
        
        public Guid Id => _id;
        
        public IMockObjectAttributes Attributes 
        { 
            get => _attributes;
            set => _attributes = value as MockObjectAttributes ?? _attributes;
        }
        
        public GeometryBase? Geometry => _geometry;
        
        public ObjectType ObjectType => ObjectType.None;
    }
    
    public class MockObjectAttributes : IMockObjectAttributes
    {
        private Color _objectColor = Color.White;
        private int _layerIndex = 0;
        private ObjectColorSource _colorSource = ObjectColorSource.ColorFromObject;
        
        public Color ObjectColor
        {
            get => _objectColor;
            set => _objectColor = value;
        }
        
        public int LayerIndex
        {
            get => _layerIndex;
            set => _layerIndex = value;
        }
        
        public ObjectColorSource ColorSource
        {
            get => _colorSource;
            set => _colorSource = value;
        }
    }
} 