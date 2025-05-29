#!/usr/bin/env python3
"""
Simple Calculator MCP Server for testing
"""

import json
import sys
import asyncio
from typing import Any, Dict, List

class CalculatorServer:
    def __init__(self):
        self.tools = [
            {
                "name": "calculate",
                "description": "Perform basic arithmetic operations",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "expression": {
                            "type": "string",
                            "description": "Mathematical expression to evaluate (e.g., '2 + 2', '10 * 5')"
                        }
                    },
                    "required": ["expression"]
                }
            }
        ]

    async def handle_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming MCP messages"""
        method = message.get("method")
        params = message.get("params", {})
        msg_id = message.get("id")

        try:
            if method == "initialize":
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {
                            "tools": {}
                        },
                        "serverInfo": {
                            "name": "calculator-server",
                            "version": "1.0.0"
                        }
                    }
                }
            
            elif method == "tools/list":
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "tools": self.tools
                    }
                }
            
            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                
                if tool_name == "calculate":
                    expression = arguments.get("expression", "")
                    try:
                        # Simple evaluation - in production, use a safer parser
                        result = eval(expression)
                        return {
                            "jsonrpc": "2.0",
                            "id": msg_id,
                            "result": {
                                "content": [
                                    {
                                        "type": "text",
                                        "text": f"The result of {expression} is {result}"
                                    }
                                ]
                            }
                        }
                    except Exception as e:
                        return {
                            "jsonrpc": "2.0",
                            "id": msg_id,
                            "error": {
                                "code": -32602,
                                "message": f"Invalid expression: {str(e)}"
                            }
                        }
                
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {
                        "code": -32601,
                        "message": f"Unknown tool: {tool_name}"
                    }
                }
            
            elif method == "sampling/createMessage":
                messages = params.get("messages", [])
                last_message = messages[-1] if messages else {}
                content = last_message.get("content", {})
                text = content.get("text", "") if isinstance(content, dict) else str(content)
                
                # Simple response logic
                if "calculate" in text.lower() or any(op in text for op in ['+', '-', '*', '/', '=']):
                    response = "I can help you with calculations! Use the calculate tool or just ask me to calculate something."
                else:
                    response = f"Hello! I'm a calculator server. I can help with math operations. You said: {text}"
                
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": response
                            }
                        ],
                        "model": "calculator-server",
                        "stopReason": "completed"
                    }
                }
            
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {
                        "code": -32601,
                        "message": f"Unknown method: {method}"
                    }
                }
                
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            }

async def main():
    """Main server loop"""
    server = CalculatorServer()
    
    while True:
        try:
            # Read message from stdin
            line = sys.stdin.readline()
            if not line:
                break
                
            message = json.loads(line.strip())
            response = await server.handle_message(message)
            
            # Write response to stdout
            print(json.dumps(response), flush=True)
            
        except json.JSONDecodeError:
            error_response = {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32700,
                    "message": "Parse error"
                }
            }
            print(json.dumps(error_response), flush=True)
        except Exception as e:
            error_response = {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            }
            print(json.dumps(error_response), flush=True)

if __name__ == "__main__":
    asyncio.run(main())