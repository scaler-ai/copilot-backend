"""
Simple WebSocket test client for MCP endpoints.
"""

import asyncio
import json
import websockets
import uuid


async def test_mcp_websocket():
    """Test the MCP WebSocket endpoint."""
    
    # First, you need to get a valid JWT token by logging in
    # For this test, replace with an actual token
    TOKEN = "YOUR_JWT_TOKEN_HERE"
    SERVER_ID = str(uuid.uuid4())  # Replace with actual server ID
    SESSION_ID = str(uuid.uuid4())  # Generate new session ID
    
    uri = f"ws://localhost:8000/api/v1/mcp/ws/mcp/{SERVER_ID}/{SESSION_ID}?token={TOKEN}"
    
    try:
        async with websockets.connect(uri) as websocket:
            print(f"Connected to WebSocket")
            
            # Wait for connection message
            response = await websocket.recv()
            print(f"Received: {response}")
            
            # Send a test message
            test_message = {
                "type": "request",
                "id": str(uuid.uuid4()),
                "method": "tools/list",
                "params": {}
            }
            
            await websocket.send(json.dumps(test_message))
            print(f"Sent: {test_message}")
            
            # Wait for response
            response = await websocket.recv()
            print(f"Received: {response}")
            
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    print("MCP WebSocket Test Client")
    print("========================")
    print("Make sure to:")
    print("1. Start the backend server")
    print("2. Create a user and get a JWT token")
    print("3. Create an MCP server")
    print("4. Update TOKEN and SERVER_ID in this script")
    print()
    
    # Uncomment to run the test
    # asyncio.run(test_mcp_websocket())