# RhinoMcpPlugin Tests

This project contains unit tests for the RhinoMcpPlugin, a core component of the RhinoMCP project that integrates the Model Context Protocol with Rhino3D.

## Overview

The test suite is organized into several categories of tests:

- **Plugin Lifecycle Tests**: Testing the plugin's initialization, loading, and shutdown processes
- **Socket Server Tests**: Testing the communication layer that handles MCP commands
- **Geometry Tools Tests**: Testing the creation and manipulation of 3D geometry
- **Scene Tools Tests**: Testing scene management functions
- **Utility Tests**: Testing helper functions and utilities

## Getting Started

### Prerequisites

- Visual Studio 2022 or later (or Visual Studio Code with C# extensions)
- .NET 7.0 SDK
- NUnit 3 Test Adapter (for running tests in Visual Studio)

### Building the Tests

1. Open the RhinoMcpPlugin solution in Visual Studio or VS Code
2. Build the RhinoMcpPlugin.Tests project

### Running the Tests

#### From Visual Studio

1. Open the Test Explorer window (Test > Test Explorer)
2. Click "Run All" to run all tests, or select specific tests to run

#### From Visual Studio Code

1. **Install the required VS Code extensions**:
   - C# Dev Kit extension (which includes the C# extension)
   - .NET Core Test Explorer extension

2. **Configure test discovery in VS Code**:
   - Open the workspace settings (File > Preferences > Settings)
   - Search for "test"
   - Under Extensions > .NET Core Test Explorer, set the test project path to include your test project:
     ```json
     "dotnet-test-explorer.testProjectPath": "**/RhinoMcpPlugin.Tests.csproj"
     ```

3. **Run the tests**:
   - You can use the Test Explorer UI (click the flask icon in the sidebar)
   - Click the run or debug icons next to individual tests or test classes
   - Right-click on tests to run, debug, or view specific tests

4. **Debug tests**:
   - Set breakpoints in your test code
   - Use the "Debug Test" option in the Test Explorer
   - Make sure your launch.json is configured correctly for .NET debugging

#### From Command Line

```
dotnet test RhinoMcpPlugin.Tests/RhinoMcpPlugin.Tests.csproj
```

To run a specific category of tests:

```
dotnet test RhinoMcpPlugin.Tests/RhinoMcpPlugin.Tests.csproj --filter "Category=Utilities"
```

To run a specific test class:

```
dotnet test RhinoMcpPlugin.Tests/RhinoMcpPlugin.Tests.csproj --filter "FullyQualifiedName~RhinoUtilitiesTests"
```

## Project Structure

- `/Tests`: Contains all test classes organized by component
- `/Mocks`: Contains mock implementations of Rhino objects for testing
- `/Framework`: Contains test helpers and base classes

## Testing Strategy

### Mocking Approach

Since the RhinoMcpPlugin relies heavily on Rhino's API, we use two mocking strategies:

1. **Custom Mock Classes**: For core Rhino objects like RhinoDoc, we've created custom mock implementations that inherit from Rhino classes.
2. **Moq Framework**: For simpler dependencies and interfaces, we use the Moq library.

### Test Isolation

Each test is designed to be independent and should not rely on the state from other tests. Tests follow this structure:

1. **Arrange**: Set up the test environment and data
2. **Act**: Perform the action being tested
3. **Assert**: Verify the expected outcome
4. **Cleanup**: Release any resources (usually handled in TearDown methods)

## Writing New Tests

### Test Naming Convention

Tests should follow this naming pattern:

```
MethodName_Scenario_ExpectedBehavior
```

For example:
- `ParseHexColor_ValidHexWithHash_ReturnsCorrectColor`
- `Start_WhenCalled_ServerStarts`

### Test Categories

Use NUnit's Category attribute to organize tests:

```csharp
[Test]
[Category("Utilities")]
public void MyTest()
{
    // Test implementation
}
```

Available categories:
- `Utilities`
- `SocketServer`
- `Plugin`
- `Geometry`
- `Commands`

### Sample Test

```csharp
[Test]
[Category("Utilities")]
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
```

## Common Issues and Solutions

### Test Cannot Find RhinoCommon.dll

Make sure the project has a correct reference to RhinoCommon.dll. In the `.csproj` file, the reference should be:

```xml
<Reference Include="RhinoCommon">
  <HintPath>$(RhinoPath)\RhinoCommon.dll</HintPath>
  <Private>False</Private>
</Reference>
```

You may need to set the `RhinoPath` environment variable to your Rhino installation directory.

### VS Code Test Discovery Issues

If VS Code is not discovering your tests:

1. Make sure you've installed the .NET Core Test Explorer extension
2. Check that your settings.json includes the correct test project path
3. Try refreshing the test explorer (click the refresh icon)
4. Ensure your tests have the `[Test]` attribute and are in public classes

### Socket Server Tests Are Flaky

Socket server tests can sometimes be flaky due to timing issues. Try:

1. Increasing the sleep duration between server start and client connection
2. Using dedicated test ports to avoid conflicts
3. Adding retry logic for connection attempts

## Contributing

When contributing new tests:

1. Follow the established naming conventions and patterns
2. Add tests to the appropriate test class or create a new one if needed
3. Use appropriate assertions for clear failure messages
4. Document any complex test scenarios
5. Run the full test suite before submitting changes

## References

- [NUnit Documentation](https://docs.nunit.org/)
- [Moq Documentation](https://github.com/moq/moq4)
- [RhinoCommon API Reference](https://developer.rhino3d.com/api/rhinocommon/)
- [VS Code .NET Testing](https://code.visualstudio.com/docs/languages/dotnet#_testing)
- [.NET Core Test Explorer](https://marketplace.visualstudio.com/items?itemName=formulahendry.dotnet-test-explorer) 