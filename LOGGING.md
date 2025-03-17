# RhinoMcpServer Logging System

This document describes the unified logging system for the RhinoMcpServer project and provides instructions on how to use the log management tools.

## Overview

The logging system centralizes logs from all components of the system:

1. **Server Logs**: From the MCP server
2. **Plugin Logs**: From the Rhino plugin
3. **Claude Logs**: Messages from Claude AI
4. **Diagnostic Logs**: Results from diagnostic tools

All logs are stored in a structured format in the `logs/` directory with separate subdirectories for each component.

## Log Directory Structure

```
logs/
├── server/         # MCP server logs
│   ├── server_YYYY-MM-DD.log
│   └── debug_YYYY-MM-DD.log
├── plugin/         # Rhino plugin logs
├── claude/         # Claude AI message logs
└── diagnostics/    # Diagnostic tool logs
```

## Log Format

The standard log format is:

```
[TIMESTAMP] [LEVEL] [COMPONENT] MESSAGE
```

Example:
```
[2023-06-15 14:32:05] [INFO] [server] RhinoMCP server starting up
```

## Using the Log Manager

The `log_manager.py` script provides a comprehensive set of tools for working with logs. Make it executable and run it with various commands:

```bash
chmod +x log_manager.py
./log_manager.py <command> [options]
```

### Available Commands

#### View Logs

```bash
# View all logs
./log_manager.py view

# View logs from the last hour
./log_manager.py view --since 1h

# View only error logs
./log_manager.py view --level ERROR

# View only server logs
./log_manager.py view --component server

# Show source files and limit to 50 entries
./log_manager.py view --source --max 50
```

#### Monitor Logs in Real-time

```bash
# Monitor all logs in real-time
./log_manager.py monitor

# Monitor only errors and warnings
./log_manager.py monitor --level ERROR,WARNING

# Monitor server and plugin logs with faster refresh
./log_manager.py monitor --component server,plugin --interval 0.5
```

#### View Errors with Context

```bash
# View all errors with context
./log_manager.py errors

# Customize context lines
./log_manager.py errors --context 10
```

#### Generate Error Reports

```bash
# Generate an error report
./log_manager.py report

# Save the report to a file
./log_manager.py report --output error_report.txt
```

#### View Log Information

```bash
# Show information about available logs
./log_manager.py info
```

#### Clear Old Logs

```bash
# Clear logs older than 7 days
./log_manager.py clear --older-than 7

# Clear only Claude logs
./log_manager.py clear --component claude

# Force deletion without confirmation
./log_manager.py clear --older-than 30 --force
```

## Diagnostic Tool

The `diagnose_rhino_connection.py` script has been updated to use the unified logging system. It now saves detailed logs to `logs/diagnostics/` for better troubleshooting.

To run the diagnostic tool:

```bash
./diagnose_rhino_connection.py
```

## Claude Integration

Claude AI can now log messages to the system using the `log_claude_message` tool. This helps track AI-generated content and troubleshoot any issues related to Claude's understanding or responses.

## Development Guidelines

1. Use the appropriate log levels:
   - `DEBUG`: Detailed information for debugging
   - `INFO`: General operational information
   - `WARNING`: Issues that don't affect functionality but are noteworthy
   - `ERROR`: Issues that prevent functionality from working properly
   - `CRITICAL`: Severe issues requiring immediate attention

2. Include a component identifier in all logs to help with filtering and troubleshooting.

3. For error logs, include sufficient context and traceback information.

4. Use request/tool IDs to correlate related log entries for complex operations.

## Troubleshooting Common Issues

1. **Missing Logs**: Check if the log directories exist and have appropriate permissions.

2. **Null Reference Errors**: Use the error report function to identify patterns in null reference errors and pinpoint their source.

3. **Connection Issues**: Run the diagnostic tool and check server logs together to correlate connection problems.

4. **Plugin Problems**: Compare server and plugin logs for the same timeframe to identify mismatches in expected behavior.

---

For additional help or questions, please refer to the project documentation or open an issue on the project repository. 