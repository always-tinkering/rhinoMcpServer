#!/usr/bin/env python3
"""
Log Manager Utility for RhinoMcpServer

This script helps manage, view, and analyze logs from the MCP Server,
Rhino plugin, Claude AI, and diagnostic tools. It provides a unified
view of logs across all components to aid in debugging.
"""

import os
import sys
import re
import glob
import argparse
from datetime import datetime, timedelta
import json
import subprocess

# Define the log directory structure
LOG_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
SERVER_LOGS = os.path.join(LOG_ROOT, "server")
PLUGIN_LOGS = os.path.join(LOG_ROOT, "plugin")
CLAUDE_LOGS = os.path.join(LOG_ROOT, "claude")
DIAGNOSTIC_LOGS = os.path.join(LOG_ROOT, "diagnostics")

# Log entry pattern for parsing - matches standard timestamp format
LOG_PATTERN = re.compile(r'^\[(?P<timestamp>.*?)\] \[(?P<level>.*?)\] \[(?P<component>.*?)\] (?P<message>.*)$')

class LogEntry:
    """Represents a parsed log entry with timestamp and metadata"""
    
    def __init__(self, timestamp, level, component, message, source_file):
        self.timestamp = timestamp
        self.level = level.upper()
        self.component = component
        self.message = message
        self.source_file = source_file
    
    @classmethod
    def from_line(cls, line, source_file):
        """Parse a log line into a LogEntry object"""
        match = LOG_PATTERN.match(line)
        if match:
            try:
                timestamp = datetime.strptime(match.group('timestamp'), '%Y-%m-%d %H:%M:%S,%f')
            except ValueError:
                try:
                    timestamp = datetime.strptime(match.group('timestamp'), '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    # If timestamp can't be parsed, use current time
                    timestamp = datetime.now()
            
            return cls(
                timestamp, 
                match.group('level'), 
                match.group('component'), 
                match.group('message'),
                source_file
            )
        return None

    def __lt__(self, other):
        """Support sorting by timestamp"""
        return self.timestamp < other.timestamp
    
    def to_string(self, colors=True, show_source=False):
        """Format the log entry for display"""
        # Define ANSI color codes
        color_map = {
            "DEBUG": "\033[36m",  # Cyan
            "INFO": "\033[32m",   # Green
            "WARNING": "\033[33m", # Yellow
            "ERROR": "\033[31m",  # Red
            "CRITICAL": "\033[41m\033[97m"  # White on red background
        }
        component_colors = {
            "server": "\033[94m",  # Blue
            "plugin": "\033[95m",  # Magenta
            "diagnostic": "\033[96m",  # Cyan
            "claude": "\033[92m"   # Green
        }
        reset = "\033[0m"
        
        # Format timestamp
        timestamp_str = self.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        
        # Apply colors if enabled
        if colors:
            level_color = color_map.get(self.level, "") 
            comp_color = component_colors.get(self.component, "")
            
            if self.level in ["ERROR", "CRITICAL"]:
                # For errors, color the whole line
                source_info = f" ({os.path.basename(self.source_file)})" if show_source else ""
                return f"{level_color}[{timestamp_str}] [{self.level}] [{self.component}] {self.message}{source_info}{reset}"
            else:
                # For non-errors, color just the level and component
                source_info = f" ({os.path.basename(self.source_file)})" if show_source else ""
                return f"[{timestamp_str}] [{level_color}{self.level}{reset}] [{comp_color}{self.component}{reset}] {self.message}{source_info}"
        else:
            source_info = f" ({os.path.basename(self.source_file)})" if show_source else ""
            return f"[{timestamp_str}] [{self.level}] [{self.component}] {self.message}{source_info}"

def collect_logs(since=None, level_filter=None, component_filter=None):
    """Collect and parse logs from all sources
    
    Args:
        since: Datetime object for filtering logs by age
        level_filter: List of log levels to include (DEBUG, INFO, etc)
        component_filter: List of components to include (server, plugin, etc)
    
    Returns:
        List of LogEntry objects sorted by timestamp
    """
    all_entries = []
    
    # Create directories if they don't exist
    for directory in [LOG_ROOT, SERVER_LOGS, PLUGIN_LOGS, CLAUDE_LOGS, DIAGNOSTIC_LOGS]:
        os.makedirs(directory, exist_ok=True)
    
    # Gather log files from all directories
    log_files = []
    log_files.extend(glob.glob(os.path.join(SERVER_LOGS, "*.log")))
    log_files.extend(glob.glob(os.path.join(PLUGIN_LOGS, "*.log")))
    log_files.extend(glob.glob(os.path.join(DIAGNOSTIC_LOGS, "*.log")))
    
    # Also check for Claude logs but handle them differently
    claude_files = glob.glob(os.path.join(CLAUDE_LOGS, "*.log"))
    
    # Process standard log files
    for log_file in log_files:
        try:
            with open(log_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    entry = LogEntry.from_line(line, log_file)
                    if entry:
                        # Apply filters
                        if since and entry.timestamp < since:
                            continue
                        if level_filter and entry.level not in level_filter:
                            continue
                        if component_filter and entry.component not in component_filter:
                            continue
                        
                        all_entries.append(entry)
        except Exception as e:
            print(f"Error processing {log_file}: {e}", file=sys.stderr)
    
    # Handle Claude logs which have a different format
    for claude_file in claude_files:
        try:
            # Get file creation time to use as timestamp
            file_time = datetime.fromtimestamp(os.path.getctime(claude_file))
            
            # Skip if it's before our filter time
            if since and file_time < since:
                continue
            
            # Only include preview of Claude logs since they can be large
            with open(claude_file, 'r') as f:
                content = f.read(500)  # Just read first 500 chars
                truncated = len(content) < os.path.getsize(claude_file)
                message = content + ("..." if truncated else "")
                
                # Create a synthetic log entry
                entry = LogEntry(
                    file_time,
                    "INFO", 
                    "claude", 
                    f"Claude interaction: {message}",
                    claude_file
                )
                
                # Apply filters
                if not component_filter or "claude" in component_filter:
                    all_entries.append(entry)
        except Exception as e:
            print(f"Error processing Claude log {claude_file}: {e}", file=sys.stderr)
    
    # Sort all entries by timestamp
    all_entries.sort()
    return all_entries

def display_logs(entries, colors=True, show_source=False, max_entries=None):
    """Display log entries with optional formatting
    
    Args:
        entries: List of LogEntry objects
        colors: Whether to use ANSI colors in output
        show_source: Whether to show source filename
        max_entries: Maximum number of entries to show (None for all)
    """
    # Maybe limit entries
    if max_entries is not None and len(entries) > max_entries:
        skipped = len(entries) - max_entries
        entries = entries[-max_entries:]
        print(f"... (skipped {skipped} earlier entries) ...\n")
    
    for entry in entries:
        print(entry.to_string(colors=colors, show_source=show_source))
        
def extract_error_context(entries, context_lines=5):
    """Extract log entries around errors with context
    
    Args:
        entries: List of all LogEntry objects
        context_lines: Number of log lines before and after each error
        
    Returns:
        List of error contexts (each being a list of LogEntry objects)
    """
    error_contexts = []
    error_indices = [i for i, entry in enumerate(entries) if entry.level in ["ERROR", "CRITICAL"]]
    
    for error_idx in error_indices:
        # Get context before and after error
        start_idx = max(0, error_idx - context_lines)
        end_idx = min(len(entries), error_idx + context_lines + 1)
        
        # Extract the context
        context = entries[start_idx:end_idx]
        error_contexts.append(context)
    
    return error_contexts

def generate_error_report(entries):
    """Generate a summary report of errors
    
    Args:
        entries: List of LogEntry objects
        
    Returns:
        String containing the error report
    """
    error_entries = [e for e in entries if e.level in ["ERROR", "CRITICAL"]]
    
    if not error_entries:
        return "No errors found in logs."
    
    # Group errors by component
    errors_by_component = {}
    for entry in error_entries:
        if entry.component not in errors_by_component:
            errors_by_component[entry.component] = []
        errors_by_component[entry.component].append(entry)
    
    # Generate the report
    report = f"Error Report ({len(error_entries)} errors found)\n"
    report += "=" * 50 + "\n\n"
    
    for component, errors in errors_by_component.items():
        report += f"{component.upper()} Errors: {len(errors)}\n"
        report += "-" * 30 + "\n"
        
        # Group by error message pattern
        error_patterns = {}
        for error in errors:
            # Simplify message by removing variable parts (numbers, IDs, etc)
            simplified = re.sub(r'\b(?:\w+[-_])?[0-9a-f]{8}(?:[-_]\w+)?\b', 'ID', error.message)
            simplified = re.sub(r'\d+', 'N', simplified)
            
            if simplified not in error_patterns:
                error_patterns[simplified] = []
            error_patterns[simplified].append(error)
        
        # Report each error pattern
        for pattern, pattern_errors in error_patterns.items():
            report += f"\n• {pattern} ({len(pattern_errors)} occurrences)\n"
            report += f"  First seen: {pattern_errors[0].timestamp}\n"
            report += f"  Last seen: {pattern_errors[-1].timestamp}\n"
            report += f"  Example: {pattern_errors[-1].message}\n"
        
        report += "\n" + "=" * 50 + "\n\n"
    
    return report

def clear_logs(days_old=None, component=None, confirm=True):
    """Clear logs based on specified criteria
    
    Args:
        days_old: Delete logs older than this many days
        component: Only delete logs from this component
        confirm: Whether to prompt for confirmation
    """
    # Determine which directories to clean
    dirs_to_clean = []
    if component == "server" or component is None:
        dirs_to_clean.append(SERVER_LOGS)
    if component == "plugin" or component is None:
        dirs_to_clean.append(PLUGIN_LOGS)
    if component == "claude" or component is None:
        dirs_to_clean.append(CLAUDE_LOGS)
    if component == "diagnostic" or component is None:
        dirs_to_clean.append(DIAGNOSTIC_LOGS)
    
    # Collect files to delete
    files_to_delete = []
    for directory in dirs_to_clean:
        for log_file in glob.glob(os.path.join(directory, "*.log")):
            if days_old is not None:
                # Check file age
                file_time = datetime.fromtimestamp(os.path.getmtime(log_file))
                cutoff_time = datetime.now() - timedelta(days=days_old)
                if file_time >= cutoff_time:
                    continue  # Skip files newer than cutoff
            
            files_to_delete.append(log_file)
    
    # Nothing to delete
    if not files_to_delete:
        print("No logs found matching the specified criteria.")
        return
    
    # Confirm deletion
    if confirm:
        print(f"Will delete {len(files_to_delete)} log files:")
        for f in files_to_delete[:5]:
            print(f"  - {os.path.basename(f)}")
        
        if len(files_to_delete) > 5:
            print(f"  - ... and {len(files_to_delete) - 5} more")
        
        confirmation = input("Proceed with deletion? (y/N): ").lower()
        if confirmation != 'y':
            print("Deletion cancelled.")
            return
    
    # Delete the files
    deleted_count = 0
    for log_file in files_to_delete:
        try:
            os.remove(log_file)
            deleted_count += 1
        except Exception as e:
            print(f"Error deleting {log_file}: {e}")
    
    print(f"Successfully deleted {deleted_count} log files.")

def monitor_logs(interval=1.0, colors=True, level_filter=None, component_filter=None):
    """Monitor logs in real-time like 'tail -f'
    
    Args:
        interval: Polling interval in seconds
        colors: Whether to use ANSI colors
        level_filter: Optional list of log levels to show
        component_filter: Optional list of components to show
    """
    print(f"Monitoring logs (Ctrl+C to exit)...")
    print(f"Filters: levels={level_filter or 'all'}, components={component_filter or 'all'}")
    
    # Get initial log entries and remember the latest timestamp
    entries = collect_logs(level_filter=level_filter, component_filter=component_filter)
    last_timestamp = entries[-1].timestamp if entries else datetime.now()
    
    try:
        while True:
            # Wait for the specified interval
            sys.stdout.flush()
            subprocess.call("", shell=True)  # Hack to make ANSI colors work in Windows
            
            # Get new entries since the last check
            new_entries = collect_logs(
                since=last_timestamp, 
                level_filter=level_filter,
                component_filter=component_filter
            )
            
            # Update timestamp for the next iteration
            if new_entries:
                last_timestamp = new_entries[-1].timestamp
                
                # Display new entries
                for entry in new_entries:
                    print(entry.to_string(colors=colors, show_source=True))
            
            # Sleep before checking again
            import time
            time.sleep(interval)
    
    except KeyboardInterrupt:
        print("\nStopped monitoring logs.")

def main():
    """Parse arguments and execute requested command"""
    parser = argparse.ArgumentParser(description="Manage and view RhinoMcpServer logs")
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # view command
    view_parser = subparsers.add_parser("view", help="View logs")
    view_parser.add_argument("--since", type=str, help="Show logs since (e.g. '1h', '2d', '30m')")
    view_parser.add_argument("--level", type=str, help="Filter by log level (comma-separated: DEBUG,INFO,WARNING,ERROR)")
    view_parser.add_argument("--component", type=str, help="Filter by component (comma-separated: server,plugin,claude,diagnostic)")
    view_parser.add_argument("--no-color", action="store_true", help="Disable colored output")
    view_parser.add_argument("--source", action="store_true", help="Show source log file")
    view_parser.add_argument("--max", type=int, help="Maximum number of entries to display")
    
    # errors command
    errors_parser = subparsers.add_parser("errors", help="View errors with context")
    errors_parser.add_argument("--since", type=str, help="Show errors since (e.g. '1h', '2d', '30m')")
    errors_parser.add_argument("--component", type=str, help="Filter by component")
    errors_parser.add_argument("--context", type=int, default=5, help="Number of context lines before/after each error")
    errors_parser.add_argument("--no-color", action="store_true", help="Disable colored output")
    
    # report command
    report_parser = subparsers.add_parser("report", help="Generate error report")
    report_parser.add_argument("--since", type=str, help="Include errors since (e.g. '1h', '2d', '30m')")
    report_parser.add_argument("--output", type=str, help="Output file for the report")
    
    # clear command
    clear_parser = subparsers.add_parser("clear", help="Clear logs")
    clear_parser.add_argument("--older-than", type=int, help="Delete logs older than N days")
    clear_parser.add_argument("--component", type=str, help="Only clear logs for the specified component")
    clear_parser.add_argument("--force", action="store_true", help="Do not ask for confirmation")
    
    # monitor command
    monitor_parser = subparsers.add_parser("monitor", help="Monitor logs in real-time")
    monitor_parser.add_argument("--interval", type=float, default=1.0, help="Polling interval in seconds")
    monitor_parser.add_argument("--level", type=str, help="Filter by log level (comma-separated)")
    monitor_parser.add_argument("--component", type=str, help="Filter by component (comma-separated)")
    monitor_parser.add_argument("--no-color", action="store_true", help="Disable colored output")
    
    # info command
    info_parser = subparsers.add_parser("info", help="Show information about logs")
    
    args = parser.parse_args()
    
    # Handle time expressions like "1h", "2d", etc.
    since_time = None
    if hasattr(args, 'since') and args.since:
        try:
            # Parse time expressions
            value = int(args.since[:-1])
            unit = args.since[-1].lower()
            
            if unit == 'h':
                since_time = datetime.now() - timedelta(hours=value)
            elif unit == 'm':
                since_time = datetime.now() - timedelta(minutes=value)
            elif unit == 'd':
                since_time = datetime.now() - timedelta(days=value)
            else:
                print(f"Invalid time unit in '{args.since}'. Use 'm' for minutes, 'h' for hours, 'd' for days.")
                return 1
        except ValueError:
            print(f"Invalid time format: '{args.since}'. Use e.g. '1h', '30m', '2d'")
            return 1
    
    # Parse level and component filters
    level_filter = None
    if hasattr(args, 'level') and args.level:
        level_filter = [l.strip().upper() for l in args.level.split(',')]
    
    component_filter = None
    if hasattr(args, 'component') and args.component:
        component_filter = [c.strip().lower() for c in args.component.split(',')]
    
    # Execute the requested command
    if args.command == "view":
        entries = collect_logs(since=since_time, level_filter=level_filter, component_filter=component_filter)
        if not entries:
            print("No log entries found matching the criteria.")
            return 0
        
        display_logs(
            entries, 
            colors=not args.no_color, 
            show_source=args.source, 
            max_entries=args.max
        )
    
    elif args.command == "errors":
        # Collect all entries first
        all_entries = collect_logs(since=since_time, component_filter=component_filter)
        if not all_entries:
            print("No log entries found.")
            return 0
        
        # Extract errors with context
        error_contexts = extract_error_context(all_entries, context_lines=args.context)
        if not error_contexts:
            print("No errors found in the logs.")
            return 0
        
        # Display each error with its context
        for i, context in enumerate(error_contexts):
            if i > 0:
                print("\n" + "-" * 80 + "\n")
            
            print(f"Error {i+1} of {len(error_contexts)}:")
            for entry in context:
                print(entry.to_string(colors=not args.no_color, show_source=True))
    
    elif args.command == "report":
        entries = collect_logs(since=since_time)
        if not entries:
            print("No log entries found.")
            return 0
        
        report = generate_error_report(entries)
        
        if args.output:
            with open(args.output, 'w') as f:
                f.write(report)
            print(f"Error report saved to {args.output}")
        else:
            print(report)
    
    elif args.command == "clear":
        clear_logs(
            days_old=args.older_than,
            component=args.component,
            confirm=not args.force
        )
    
    elif args.command == "monitor":
        monitor_logs(
            interval=args.interval,
            colors=not args.no_color,
            level_filter=level_filter,
            component_filter=component_filter
        )
    
    elif args.command == "info":
        # Show information about available logs
        print("Log Directory Structure:")
        print(f"  Root: {LOG_ROOT}")
        
        # Helper function to summarize logs in a directory
        def summarize_dir(dir_path, name):
            if not os.path.exists(dir_path):
                return f"{name}: Directory not found"
            
            log_files = glob.glob(os.path.join(dir_path, "*.log"))
            if not log_files:
                return f"{name}: No log files found"
            
            newest = max(log_files, key=os.path.getmtime)
            oldest = min(log_files, key=os.path.getmtime)
            newest_time = datetime.fromtimestamp(os.path.getmtime(newest))
            oldest_time = datetime.fromtimestamp(os.path.getmtime(oldest))
            
            total_size = sum(os.path.getsize(f) for f in log_files)
            size_mb = total_size / (1024 * 1024)
            
            return (f"{name}: {len(log_files)} files, {size_mb:.2f} MB total\n"
                    f"  Newest: {os.path.basename(newest)} ({newest_time})\n"
                    f"  Oldest: {os.path.basename(oldest)} ({oldest_time})")
        
        print("\nLog Summaries:")
        print(summarize_dir(SERVER_LOGS, "Server Logs"))
        print(summarize_dir(PLUGIN_LOGS, "Plugin Logs"))
        print(summarize_dir(CLAUDE_LOGS, "Claude Logs"))
        print(summarize_dir(DIAGNOSTIC_LOGS, "Diagnostic Logs"))
    
    else:
        parser.print_help()
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 