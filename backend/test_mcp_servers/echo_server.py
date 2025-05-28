#!/usr/bin/env python3
"""
Simple echo MCP server for testing - just echoes back messages.
"""

import sys
import json

# Simple echo - read from stdin, echo to stdout
while True:
    try:
        line = sys.stdin.readline()
        if not line:
            break
        
        # Parse and echo back
        try:
            request = json.loads(line.strip())
            response = {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "result": {
                    "echo": f"Received: {request.get('method', 'unknown')}"
                }
            }
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()
        except:
            pass
            
    except KeyboardInterrupt:
        break