#!/bin/bash
echo "Starting RhinoMcpServer..."
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
echo "Server directory: $DIR"
echo "Full path: $DIR/publish/RhinoMcpServer.dll"
echo "Executing dotnet command..."
dotnet "$DIR/publish/RhinoMcpServer.dll" --verbose 2>&1 | tee "$DIR/server.log" 