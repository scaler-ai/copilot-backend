#!/usr/bin/env python3
"""
Example STDIO MCP server for testing.

This server implements a simple calculator with basic math operations.
Communication happens via stdin/stdout using JSON-RPC format.
"""

import sys
import json
import uuid
from typing import Dict, Any, Optional


class StdioMCPServer:
    """Simple MCP server that communicates via stdio."""
    
    def __init__(self):
        self.tools = {
            "add": {
                "description": "Add two numbers",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "a": {"type": "number"},
                        "b": {"type": "number"}
                    },
                    "required": ["a", "b"]
                }
            },
            "multiply": {
                "description": "Multiply two numbers",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "a": {"type": "number"},
                        "b": {"type": "number"}
                    },
                    "required": ["a", "b"]
                }
            },
            "greet": {
                "description": "Generate a greeting",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"}
                    },
                    "required": ["name"]
                }
            }
        }
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle an incoming JSON-RPC request."""
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")
        
        # Handle different methods
        if method == "initialize":
            return self.initialize(request_id)
        elif method == "tools/list":
            return self.list_tools(request_id)
        elif method == "tools/call":
            return self.call_tool(request_id, params)
        else:
            return self.error_response(
                request_id,
                -32601,
                f"Method not found: {method}"
            )
    
    def initialize(self, request_id: str) -> Dict[str, Any]:
        """Handle initialization request."""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "1.0",
                "capabilities": {
                    "tools": True,
                    "prompts": False,
                    "resources": False
                },
                "serverInfo": {
                    "name": "Test Calculator Server",
                    "version": "1.0.0"
                }
            }
        }
    
    def list_tools(self, request_id: str) -> Dict[str, Any]:
        """List available tools."""
        tools_list = []
        for name, info in self.tools.items():
            tools_list.append({
                "name": name,
                "description": info["description"],
                "inputSchema": info["input_schema"]
            })
        
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "tools": tools_list
            }
        }
    
    def call_tool(self, request_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool."""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if tool_name not in self.tools:
            return self.error_response(
                request_id,
                -32602,
                f"Unknown tool: {tool_name}"
            )
        
        try:
            # Execute the tool
            if tool_name == "add":
                result = arguments["a"] + arguments["b"]
                content = f"{arguments['a']} + {arguments['b']} = {result}"
            elif tool_name == "multiply":
                result = arguments["a"] * arguments["b"]
                content = f"{arguments['a']} × {arguments['b']} = {result}"
            elif tool_name == "greet":
                content = f"Hello, {arguments['name']}! Welcome to MCP."
            else:
                content = "Tool execution failed"
            
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": content
                        }
                    ]
                }
            }
            
        except Exception as e:
            return self.error_response(
                request_id,
                -32603,
                f"Tool execution error: {str(e)}"
            )
    
    def error_response(
        self, 
        request_id: Optional[str], 
        code: int, 
        message: str
    ) -> Dict[str, Any]:
        """Create an error response."""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": code,
                "message": message
            }
        }
    
    def run(self):
        """Run the server, reading from stdin and writing to stdout."""
        sys.stderr.write("Test MCP Server started\n")
        sys.stderr.flush()
        
        while True:
            try:
                # Read a line from stdin
                line = sys.stdin.readline()
                if not line:
                    break
                
                # Parse JSON-RPC request
                try:
                    request = json.loads(line.strip())
                except json.JSONDecodeError:
                    response = self.error_response(
                        None,
                        -32700,
                        "Parse error"
                    )
                else:
                    # Handle the request
                    response = self.handle_request(request)
                
                # Send response
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                sys.stderr.write(f"Server error: {str(e)}\n")
                sys.stderr.flush()


if __name__ == "__main__":
    server = StdioMCPServer()
    server.run()