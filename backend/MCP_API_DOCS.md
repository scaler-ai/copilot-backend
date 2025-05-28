# MCP API Documentation for Frontend Integration

This document provides a comprehensive guide for frontend developers to integrate with the MCP (Model Context Protocol) backend APIs.

## Base URL
- Development: `http://localhost:8000/api/v1`
- WebSocket: `ws://localhost:8000/api/v1/mcp/ws`

## Authentication

All endpoints (except public ones) require JWT authentication.

### Getting a Token

```http
POST /login/access-token
Content-Type: application/x-www-form-urlencoded

username=user@example.com&password=password123
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

### Using the Token

Include in all authenticated requests:
```
Authorization: Bearer <token>
```

## MCP Server Management APIs

### 1. List User's MCP Servers

```http
GET /mcp/servers
Authorization: Bearer <token>
```

Response:
```json
{
  "data": [
    {
      "id": "uuid",
      "name": "My MCP Server",
      "description": "Description",
      "server_type": "stdio",
      "status": "active",
      "connection_config": {
        "command": ["python", "server.py"],
        "args": [],
        "env": {}
      },
      "capabilities": {
        "tools": ["search", "calculate"],
        "prompts": []
      },
      "is_public": false,
      "owner_id": "uuid",
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T00:00:00Z"
    }
  ],
  "count": 1
}
```

### 2. Create MCP Server

```http
POST /mcp/servers
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "My Calculator Server",
  "description": "A server that provides calculator tools",
  "server_type": "stdio",
  "connection_config": {
    "command": ["python", "calculator.py"],
    "args": [],
    "env": {}
  },
  "capabilities": {
    "tools": ["add", "subtract", "multiply"],
    "prompts": []
  },
  "is_public": false
}
```

### 3. Get Server Details

```http
GET /mcp/servers/{server_id}
Authorization: Bearer <token>
```

### 4. Update Server

```http
PUT /mcp/servers/{server_id}
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "Updated Name",
  "status": "inactive"
}
```

### 5. Delete Server

```http
DELETE /mcp/servers/{server_id}
Authorization: Bearer <token>
```

### 6. Search Servers

```http
GET /mcp/servers/search?q=calculator
Authorization: Bearer <token>
```

### 7. Get Public Servers

```http
GET /mcp/servers/public
```

No authentication required. Returns publicly available MCP servers.

### 8. Health Check Server

```http
POST /mcp/servers/{server_id}/health
Authorization: Bearer <token>
```

Response:
```json
{
  "server_id": "uuid",
  "status": "active",
  "last_check": "2024-01-01T00:00:00Z",
  "response_time_ms": 150,
  "error": null,
  "available_tools": ["add", "multiply"]
}
```

## WebSocket API for Real-time MCP Communication

### Connection URL

```
ws://localhost:8000/api/v1/mcp/ws/mcp/{server_id}/{session_id}?token={jwt_token}
```

Parameters:
- `server_id`: UUID of the MCP server to connect to
- `session_id`: UUID for the session (generate new or use existing)
- `token`: JWT authentication token (as query parameter)

### Message Protocol

All messages follow the MCP protocol format:

#### Client → Server Messages

1. **Initialize**
```json
{
  "type": "request",
  "id": "unique-request-id",
  "method": "initialize",
  "params": {}
}
```

2. **List Tools**
```json
{
  "type": "request",
  "id": "unique-request-id",
  "method": "tools/list",
  "params": {}
}
```

3. **Call Tool**
```json
{
  "type": "request",
  "id": "unique-request-id",
  "method": "tools/call",
  "params": {
    "name": "add",
    "arguments": {
      "a": 5,
      "b": 3
    }
  }
}
```

#### Server → Client Messages

1. **Connection Success**
```json
{
  "type": "connection",
  "status": "connected",
  "server": {
    "id": "server-uuid",
    "name": "Server Name",
    "type": "stdio",
    "capabilities": {}
  }
}
```

2. **Response**
```json
{
  "jsonrpc": "2.0",
  "id": "request-id",
  "result": {
    // Response data
  }
}
```

3. **Error**
```json
{
  "type": "error",
  "id": "request-id",
  "error": {
    "code": -32601,
    "message": "Method not found"
  }
}
```

## Frontend Integration Example

```javascript
// 1. Authenticate
const loginResponse = await fetch('/api/v1/login/access-token', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/x-www-form-urlencoded',
  },
  body: 'username=user@example.com&password=password123'
});
const { access_token } = await loginResponse.json();

// 2. Get servers
const serversResponse = await fetch('/api/v1/mcp/servers', {
  headers: {
    'Authorization': `Bearer ${access_token}`
  }
});
const { data: servers } = await serversResponse.json();

// 3. Connect via WebSocket
const serverId = servers[0].id;
const sessionId = crypto.randomUUID();
const ws = new WebSocket(
  `ws://localhost:8000/api/v1/mcp/ws/mcp/${serverId}/${sessionId}?token=${access_token}`
);

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log('Received:', message);
};

ws.onopen = () => {
  // Send initialize request
  ws.send(JSON.stringify({
    type: 'request',
    id: crypto.randomUUID(),
    method: 'initialize',
    params: {}
  }));
};
```

## Error Codes

- `400` - Bad Request (invalid input)
- `401` - Unauthorized (missing/invalid token)
- `403` - Forbidden (insufficient permissions)
- `404` - Not Found
- `409` - Conflict (e.g., duplicate server name)
- `500` - Internal Server Error

## Server Types

- `stdio` - Standard input/output communication
- `http` - HTTP-based MCP server (future)
- `websocket` - WebSocket-based MCP server (future)

## Server Status

- `active` - Server is running and healthy
- `inactive` - Server is stopped
- `error` - Server encountered an error
- `maintenance` - Server is under maintenance

## Testing

Use the test page at `http://localhost:8000/api/v1/mcp/test` to experiment with the APIs interactively.