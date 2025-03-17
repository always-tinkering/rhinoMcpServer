# Rhino MCP Plugin Update Guide

This document outlines the necessary changes to fix the null reference issues in the RhinoMcpPlugin and implement enhanced logging.

## Summary of Issues

Based on our analysis of logs, the main problem is that the plugin assumes an active Rhino document exists, but no checks are made to verify this. When the plugin tries to access `RhinoDoc.ActiveDoc` and it's null, a null reference exception occurs.

## Required Changes

### 1. Add NLog Framework for Logging

1. Add NLog NuGet package to your Visual Studio project:
   ```
   Install-Package NLog
   ```

2. Copy the `NLog.config` file to your project root and set its "Copy to Output Directory" property to "Copy always".

### 2. Update Plugin Framework

Replace your current plugin implementation with the updated code in `RhinoPluginFixImplementation.cs`. This update includes:

- Automatic document creation if none exists
- Detailed error handling with context
- UI thread synchronization
- Command execution on the UI thread
- Document lifecycle monitoring
- Health check command

### 3. Key Fixes Implemented

The updated plugin fixes several critical issues:

1. **Document Verification**:
   - The plugin now verifies a document exists before processing commands
   - Automatically creates a document if none exists
   - Ensures a document always exists by monitoring document close events

2. **UI Thread Execution**:
   - All document operations now run on the Rhino UI thread with `RhinoApp.InvokeOnUiThread()`
   - Prevents threading issues with Rhino's document model

3. **Error Handling**:
   - Detailed exception logging with context
   - Structured try/catch blocks in all command handlers
   - Special handling for null reference exceptions

4. **Health Check Command**:
   - Added a `health_check` command that returns the status of all critical components

## How to Implement

1. **Backup your existing plugin code**
   
2. **Add NLog Framework**:
   - Add the NLog NuGet package
   - Add the provided NLog.config to your project

3. **Update Plugin Code**:
   - Replace your existing plugin implementation with the code from `RhinoPluginFixImplementation.cs`
   - Update any custom command handlers by following the pattern in the example handlers

4. **Test the Plugin**:
   - Load the updated plugin in Rhino
   - Check that logs are created in the specified directory
   - Test the health check command to verify all components are working

## Log Analysis

Once implemented, you can use the log manager to analyze logs:

```bash
./log_manager.py view --component plugin
```

Look for entries with the `[plugin]` component tag to see detailed information about what's happening in the Rhino plugin.

## Testing the Fix

After implementing the changes, run the diagnostic script:

```bash
./diagnose_rhino_connection.py
```

This should now successfully create a box and return scene information, as the plugin will ensure a document exists and operations run on the UI thread.

## Further Customization

The updated plugin provides a framework that you can extend with additional commands. Follow these patterns:

1. Add new command handlers to the `CommandHandlers` class
2. Add the command to the `ProcessCommand` switch statement
3. Ensure all UI operations run in the `RhinoApp.InvokeOnUiThread` block
4. Use the same error handling pattern with try/catch blocks and detailed logging

## Common Issues

1. **NLog Configuration**: If logs aren't being created, check that the NLog.config file is being copied to the output directory and the paths are correct.

2. **Multiple Plugin Instances**: Ensure only one instance of the plugin is loaded in Rhino.

3. **Permissions**: Check that the plugin has permission to write to the log directory.

4. **Document Creation**: If document creation fails, there may be an issue with the Rhino environment. Check the logs for specific errors. 