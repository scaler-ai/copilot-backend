"""
Update the test MCP server to use echo command.
"""

import asyncio
import httpx
import os


async def update_server():
    """Update the MCP server configuration."""
    base_url = "http://localhost:8000/api/v1"
    
    # Test credentials
    email = "test@example.com"
    password = "TestPassword123!"
    
    async with httpx.AsyncClient() as client:
        # 1. Login to get token
        print("1. Logging in...")
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
        headers = {"Authorization": f"Bearer {token}"}
        
        # 2. Get existing servers
        print("\n2. Getting servers...")
        servers_response = await client.get(
            f"{base_url}/mcp/servers",
            headers=headers
        )
        
        if servers_response.status_code == 200:
            servers = servers_response.json()["data"]
            if servers:
                server = servers[0]  # Get first server
                server_id = server["id"]
                print(f"   Found server: {server['name']} (ID: {server_id})")
                
                # 3. Create a simple test script
                script_path = os.path.join(
                    os.path.dirname(os.path.abspath(__file__)),
                    "test_mcp_servers",
                    "stdio_server.py"
                )
                
                # Ensure script exists and is executable
                if os.path.exists(script_path):
                    os.chmod(script_path, 0o755)
                
                # 4. Update server with Python echo server
                print("\n3. Updating server configuration...")
                update_data = {
                    "connection_config": {
                        "command": ["/usr/bin/python3", script_path],
                        "args": [],
                        "env": {"PYTHONUNBUFFERED": "1"}
                    }
                }
                
                update_response = await client.put(
                    f"{base_url}/mcp/servers/{server_id}",
                    json=update_data,
                    headers=headers
                )
                
                if update_response.status_code == 200:
                    print("   ✅ Server updated successfully!")
                    print(f"\n📋 Updated Server Info:")
                    print(f"   Server ID: {server_id}")
                    print(f"   Command: /usr/bin/python3 {script_path}")
                    print(f"\n🚀 Now try connecting again!")
                else:
                    print(f"   ❌ Failed to update: {update_response.json()}")
            else:
                print("   No servers found. Run create_test_mcp_server.py first!")


if __name__ == "__main__":
    print("🔧 MCP Server Updater (Python Echo)")
    print("===================================\n")
    asyncio.run(update_server())