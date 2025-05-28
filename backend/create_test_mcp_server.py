"""
Quick script to create test data for MCP WebSocket testing.
"""

import asyncio
import httpx
import json


async def create_test_data():
    """Create a test user and MCP server."""
    base_url = "http://localhost:8000/api/v1"
    
    # Test credentials
    email = "test@example.com"
    password = "TestPassword123!"
    
    async with httpx.AsyncClient() as client:
        # 1. Try to register (might already exist)
        print("1. Registering user...")
        register_response = await client.post(
            f"{base_url}/users/signup",
            json={
                "email": email,
                "password": password,
                "full_name": "Test User"
            }
        )
        if register_response.status_code in [200, 201]:
            print("   ✅ User created successfully")
        else:
            print(f"   ℹ️  User might already exist: {register_response.json()}")
        
        # 2. Login to get token
        print("\n2. Logging in...")
        login_response = await client.post(
            f"{base_url}/login/access-token",
            data={
                "username": email,
                "password": password
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        if login_response.status_code != 200:
            print(f"   ❌ Login failed: {login_response.json()}")
            return
        
        token = login_response.json()["access_token"]
        print(f"   ✅ Got token: {token[:20]}...")
        
        # 3. Create an MCP server
        print("\n3. Creating MCP server...")
        headers = {"Authorization": f"Bearer {token}"}
        
        import os
        script_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "test_mcp_servers",
            "stdio_server.py"
        )
        
        server_data = {
            "name": "Test Calculator Server",
            "description": "A test MCP server that provides calculator tools",
            "server_type": "stdio",
            "connection_config": {
                "command": ["python", script_path],
                "args": [],
                "env": {}
            },
            "capabilities": {
                "tools": ["add", "multiply", "greet"],
                "prompts": []
            },
            "is_public": True
        }
        
        create_response = await client.post(
            f"{base_url}/mcp/servers",
            json=server_data,
            headers=headers
        )
        
        if create_response.status_code == 200:
            server = create_response.json()
            print(f"   ✅ Server created!")
            print(f"\n📋 Test Data Summary:")
            print(f"   Email: {email}")
            print(f"   Password: {password}")
            print(f"   Server ID: {server['id']}")
            print(f"   Server Name: {server['name']}")
            print(f"\n🚀 Next Steps:")
            print(f"   1. Open http://localhost:8000/api/v1/mcp/test")
            print(f"   2. Login with the credentials above")
            print(f"   3. Use Server ID: {server['id']}")
            print(f"   4. Click Connect and test the WebSocket!")
        else:
            print(f"   ❌ Failed to create server: {create_response.json()}")


if __name__ == "__main__":
    print("🔧 MCP Test Data Creator")
    print("========================\n")
    asyncio.run(create_test_data())