"""
WebSocket endpoints for MCP (Model Context Protocol) real-time communication.

This module implements WebSocket connections for:
- Real-time communication with MCP servers
- Tool execution and response streaming
- Session management with bidirectional messaging
"""

import asyncio
import json
import os
import uuid
from datetime import datetime
from typing import Dict, Optional, Any

from fastapi import WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from sqlmodel import Session

from app.api.deps import get_current_user_ws, get_db
from app.repositories.mcp_server import MCPServerRepository
from app.schemas.mcp import (
    MCPWebSocketMessage,
    MCPMessageRole,
    MCPSessionStatus,
    MCPToolExecutionStatus,
)
from app.core.logging import logger


class ConnectionManager:
    """Manages WebSocket connections for MCP sessions."""
    
    def __init__(self):
        # Active connections: {session_id: {"websocket": WebSocket, "user_id": UUID}}
        self.active_connections: Dict[str, Dict[str, Any]] = {}
        # MCP server connections: {server_id: asyncio.subprocess}
        self.mcp_processes: Dict[str, Any] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str, user_id: uuid.UUID):
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        self.active_connections[session_id] = {
            "websocket": websocket,
            "user_id": user_id,
            "connected_at": datetime.utcnow()
        }
        logger.info(f"WebSocket connected: session={session_id}, user={user_id}")
    
    def disconnect(self, session_id: str):
        """Remove a WebSocket connection."""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            logger.info(f"WebSocket disconnected: session={session_id}")
    
    async def send_message(self, session_id: str, message: dict):
        """Send a message to a specific session."""
        if session_id in self.active_connections:
            websocket = self.active_connections[session_id]["websocket"]
            await websocket.send_json(message)
    
    async def broadcast_to_user(self, user_id: uuid.UUID, message: dict):
        """Broadcast a message to all sessions of a specific user."""
        for session_id, conn in self.active_connections.items():
            if conn["user_id"] == user_id:
                await self.send_message(session_id, message)
    
    async def start_mcp_server(self, server_id: str, connection_config: dict) -> bool:
        """Start an MCP server process based on its configuration."""
        try:
            if server_id in self.mcp_processes:
                logger.warning(f"MCP server already running: {server_id}")
                return True
            
            # Extract command from connection config
            command = connection_config.get("command", [])
            args = connection_config.get("args", [])
            env = connection_config.get("env", {})
            
            # Handle command as string or list
            if isinstance(command, str):
                command = [command]
            if isinstance(args, str):
                args = [args]
            
            if not command:
                logger.error(f"No command specified for MCP server: {server_id}")
                return False
            
            # Log the command being executed
            logger.info(f"Starting MCP server {server_id}")
            logger.info(f"Command: {command}")
            logger.info(f"Args: {args}")
            logger.info(f"Full command: {command + args}")
            
            # Start the MCP server process
            process = await asyncio.create_subprocess_exec(
                *command,
                *args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**os.environ, **env}  # Include current environment
            )
            
            # Check if process started successfully
            try:
                # Wait a bit to see if process exits immediately
                await asyncio.wait_for(process.wait(), timeout=0.5)
                # If we get here, process exited
                stderr = await process.stderr.read()
                logger.error(f"MCP server {server_id} exited immediately")
                logger.error(f"Exit code: {process.returncode}")
                logger.error(f"Stderr: {stderr.decode()}")
                return False
            except asyncio.TimeoutError:
                # Process is still running, which is good
                pass
            
            self.mcp_processes[server_id] = {
                "process": process,
                "started_at": datetime.utcnow()
            }
            
            logger.info(f"Started MCP server successfully: {server_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start MCP server {server_id}: {str(e)}")
            logger.error(f"Exception type: {type(e).__name__}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
    
    async def stop_mcp_server(self, server_id: str):
        """Stop an MCP server process."""
        if server_id in self.mcp_processes:
            process = self.mcp_processes[server_id]["process"]
            process.terminate()
            await process.wait()
            del self.mcp_processes[server_id]
            logger.info(f"Stopped MCP server: {server_id}")
    
    async def send_to_mcp_server(self, server_id: str, message: dict) -> Optional[dict]:
        """Send a message to an MCP server and wait for response."""
        if server_id not in self.mcp_processes:
            logger.error(f"MCP server not running: {server_id}")
            return None
        
        try:
            process = self.mcp_processes[server_id]["process"]
            
            # Send message to MCP server stdin
            message_bytes = json.dumps(message).encode() + b'\n'
            process.stdin.write(message_bytes)
            await process.stdin.drain()
            
            # Read response from stdout
            response_line = await process.stdout.readline()
            if response_line:
                return json.loads(response_line.decode())
            
            return None
            
        except Exception as e:
            logger.error(f"Error communicating with MCP server {server_id}: {str(e)}")
            return None


# Global connection manager
manager = ConnectionManager()


async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    server_id: str,
    db: Session,
    token: str = None,
):
    """
    WebSocket endpoint for MCP communication.
    
    Handles:
    - User authentication
    - Server validation and access control
    - Message routing between client and MCP server
    - Session and message persistence
    """
    logger.info(f"WebSocket endpoint called - server_id: {server_id}, session_id: {session_id}")
    logger.info(f"Token present: {bool(token)}")
    
    # Authenticate user from WebSocket
    try:
        user = await get_current_user_ws(websocket, db, token)
        if not user:
            logger.error("No user returned from authentication")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        logger.info(f"User authenticated: {user.email}")
    except Exception as e:
        logger.error(f"WebSocket auth failed: {str(e)}")
        logger.error(f"Auth exception type: {type(e).__name__}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    
    # Validate access to MCP server
    repo = MCPServerRepository(db)
    server = await repo.get_by_id(server_id=uuid.UUID(server_id))
    
    if not server:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    
    # Check access permissions
    if server.owner_id != user.id and not server.is_public:
        # Check if user is in allowed_users or has allowed role
        if user.id not in server.allowed_users:
            # TODO: Check user roles against allowed_roles
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
    
    # Connect WebSocket
    await manager.connect(websocket, session_id, user.id)
    
    # Start MCP server if not already running
    if not await manager.start_mcp_server(str(server.id), server.connection_config):
        await websocket.send_json({
            "type": "error",
            "error": {"message": "Failed to start MCP server"}
        })
        manager.disconnect(session_id)
        return
    
    # Create or get session
    # TODO: Implement session creation/retrieval
    
    try:
        # Send initial connection success message
        await websocket.send_json({
            "type": "connection",
            "status": "connected",
            "server": {
                "id": str(server.id),
                "name": server.name,
                "type": server.server_type,
                "capabilities": server.capabilities
            }
        })
        
        # Initialize the MCP server and get tools
        logger.info("Initializing MCP server...")
        
        # Send initialize request
        init_response = await manager.send_to_mcp_server(
            str(server.id),
            {
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "Copilot MCP Host",
                        "version": "1.0.0"
                    }
                },
                "id": 1
            }
        )
        
        if init_response:
            logger.info(f"MCP server initialized: {init_response}")
            
            # Request available tools
            tools_response = await manager.send_to_mcp_server(
                str(server.id),
                {
                    "jsonrpc": "2.0",
                    "method": "tools/list",
                    "params": {},
                    "id": 2
                }
            )
            
            if tools_response and tools_response.get("result"):
                tools = tools_response["result"].get("tools", [])
                logger.info(f"Available tools: {tools}")
                
                # Send tools to frontend
                await websocket.send_json({
                    "type": "tools_available",
                    "tools": tools
                })
                
                # Update server capabilities in database with available tools
                try:
                    # Update the server's capabilities to include tools
                    updated_capabilities = server.capabilities or {}
                    updated_capabilities["tools"] = tools
                    
                    await repo.update(
                        server_id=server.id,
                        server_update={"capabilities": updated_capabilities}
                    )
                    logger.info(f"Updated server capabilities with {len(tools)} tools")
                except Exception as e:
                    logger.error(f"Failed to update server capabilities: {str(e)}")
        else:
            logger.error("Failed to initialize MCP server")
        
        # Message handling loop
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            logger.info(f"Received WebSocket message: {data}")
            
            # Handle different message types based on jsonrpc method
            method = data.get("method")
            params = data.get("params", {})
            msg_id = data.get("id")
            
            try:
                if method == "sampling/createMessage":
                    # This is a user message from the frontend
                    messages = params.get("messages", [])
                    if messages:
                        user_message = messages[0]  # Get the user message
                        content = user_message.get("content", {})
                        text = content.get("text", "") if isinstance(content, dict) else str(content)
                        
                        # Save user message to database
                        from app.repositories.mcp_session import MCPSessionRepository
                        session_repo = MCPSessionRepository(db)
                        
                        saved_message = await session_repo.add_message(
                            session_id=uuid.UUID(session_id),
                            role=MCPMessageRole.USER,
                            content=text
                        )
                        logger.info(f"Saved user message to database: {saved_message.id}")
                        
                        # Send confirmation that user message was saved
                        await websocket.send_json({
                            "type": "message_saved",
                            "message": {
                                "id": str(saved_message.id),
                                "session_id": str(saved_message.session_id),
                                "role": saved_message.role,
                                "content": saved_message.content,
                                "created_at": saved_message.created_at.isoformat()
                            }
                        })
                        
                        # Forward to MCP server
                        mcp_response = await manager.send_to_mcp_server(
                            str(server.id), 
                            data
                        )
                        
                        if mcp_response:
                            logger.info(f"Got MCP response: {mcp_response}")
                            
                            # Save assistant response to database
                            if mcp_response.get("result", {}).get("content"):
                                content_items = mcp_response["result"]["content"]
                                assistant_text = content_items[0].get("text", "") if content_items else ""
                                
                                saved_response = await session_repo.add_message(
                                    session_id=uuid.UUID(session_id),
                                    role=MCPMessageRole.ASSISTANT,
                                    content=assistant_text
                                )
                                logger.info(f"Saved assistant message to database: {saved_response.id}")
                                
                                # Send assistant message confirmation
                                await websocket.send_json({
                                    "type": "message_saved",
                                    "message": {
                                        "id": str(saved_response.id),
                                        "session_id": str(saved_response.session_id),
                                        "role": saved_response.role,
                                        "content": saved_response.content,
                                        "created_at": saved_response.created_at.isoformat()
                                    }
                                })
                            
                            # Send MCP response back to client
                            await websocket.send_json(mcp_response)
                        else:
                            await websocket.send_json({
                                "jsonrpc": "2.0",
                                "id": msg_id,
                                "error": {"message": "No response from MCP server"}
                            })
                
                elif method == "initialize":
                    # Forward initialization to MCP server
                    mcp_response = await manager.send_to_mcp_server(
                        str(server.id), 
                        data
                    )
                    
                    if mcp_response:
                        await websocket.send_json(mcp_response)
                    else:
                        await websocket.send_json({
                            "jsonrpc": "2.0",
                            "id": msg_id,
                            "error": {"message": "Failed to initialize MCP server"}
                        })
                
                else:
                    # Forward other messages to MCP server
                    mcp_response = await manager.send_to_mcp_server(
                        str(server.id),
                        data
                    )
                    
                    if mcp_response:
                        await websocket.send_json(mcp_response)
                    else:
                        await websocket.send_json({
                            "jsonrpc": "2.0",
                            "id": msg_id,
                            "error": {"message": "No response from MCP server"}
                        })
                        
            except Exception as e:
                logger.error(f"Error processing WebSocket message: {str(e)}")
                await websocket.send_json({
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {"message": f"Internal error: {str(e)}"}
                })
    
    except WebSocketDisconnect:
        manager.disconnect(session_id)
        # TODO: Update session status to completed
        
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        manager.disconnect(session_id)
        # TODO: Update session status to error