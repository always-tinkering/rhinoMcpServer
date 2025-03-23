using System;
using System.Drawing;
using NUnit.Framework;
using RhinoMcpPlugin;

namespace RhinoMcpPlugin.Tests
{
    [TestFixture]
    [Category("ColorUtil")]
    public class ColorUtilTests
    {
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
    }
} 