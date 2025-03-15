#!/usr/bin/env python3
import sys
import json
import os

def main():
    log_file = os.environ.get('JSON_LOG_FILE', '/dev/null')
    with open(log_file, 'a') as log:
        line_count = 0
        for line in sys.stdin:
            line_count += 1
            line = line.strip()
            if not line:
                continue
                
            try:
                # Try to parse as JSON to validate
                parsed = json.loads(line)
                # If successful, write to stdout for Claude to consume
                print(line)
                sys.stdout.flush()
                log.write(f"VALID JSON [{line_count}]: {line[:100]}...\n")
                log.flush()
            except json.JSONDecodeError as e:
                # If invalid JSON, log it but don't pass to stdout
                log.write(f"INVALID JSON [{line_count}]: {str(e)} in: {line[:100]}...\n")
                log.flush()

if __name__ == "__main__":
    main()
