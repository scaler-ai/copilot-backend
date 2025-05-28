"""
WebSocket routes for MCP real-time communication.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlmodel import Session

from app.api.deps import get_db
from app.api.websockets.mcp import websocket_endpoint

router = APIRouter()


@router.websocket("/ws/mcp/{server_id}/{session_id}")
async def mcp_websocket(
    websocket: WebSocket,
    server_id: str,
    session_id: str,
    token: str = Query(..., description="JWT token for authentication"),
    db: Session = Depends(get_db),
):
    """
    WebSocket endpoint for MCP server communication.
    
    Connect using:
    ws://localhost:8000/api/v1/mcp/ws/mcp/{server_id}/{session_id}?token=YOUR_JWT_TOKEN
    
    Parameters:
    - server_id: UUID of the MCP server to connect to
    - session_id: UUID of the session (create new or resume existing)
    - token: JWT authentication token (passed as query parameter)
    
    Message format follows MCP protocol:
    {
        "type": "request" | "response" | "notification",
        "id": "optional-request-id",
        "method": "method-name",
        "params": {},
        "result": {},
        "error": {}
    }
    """
    await websocket_endpoint(websocket, session_id, server_id, db, token)