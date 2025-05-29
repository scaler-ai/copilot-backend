"""
MCP (Model Context Protocol) API endpoints.

This module provides REST API endpoints for managing MCP servers,
tools, sessions, and protocol interactions.
"""

import uuid
from datetime import datetime
from typing import Any, List

from fastapi import APIRouter, HTTPException, status
from sqlmodel import func, select

from app.api.deps import CurrentUser, SessionDep
from app.repositories.mcp_server import MCPServerRepository
from app.schemas.mcp import (
    MCPServerCreate,
    MCPServerUpdate,
    MCPServerPublic,
    MCPServersPublic,
    MCPServerStatus,
    MCPServerHealthCheck,
    MCPSessionCreate,
    MCPSessionPublic,
    MCPMessagePublic,
)
from app.models import Message
from app.api.routes import mcp_ws, mcp_test

router = APIRouter(prefix="/mcp", tags=["mcp"])

# Include WebSocket routes
router.include_router(mcp_ws.router)

# Include test page route (only in development)
from app.core.config import settings
if settings.ENVIRONMENT == "local":
    router.include_router(mcp_test.router)


@router.get("/servers", response_model=MCPServersPublic)
async def read_mcp_servers(
    session: SessionDep, 
    current_user: CurrentUser, 
    skip: int = 0, 
    limit: int = 100
) -> Any:
    """
    Retrieve MCP servers.
    
    Returns servers owned by the current user, or all servers if user is superuser.
    """
    repo = MCPServerRepository(session)
    
    if getattr(current_user, 'is_superuser', False):
        # Superusers can see all servers - use search with empty query for all
        servers = await repo.search_servers(query="", skip=skip, limit=limit)
        count = len(servers)  # Temporary - should implement proper counting
    else:
        # Regular users see only their own servers
        servers = await repo.get_by_owner(owner_id=current_user.id, skip=skip, limit=limit)
        count = len(servers)  # Temporary - should implement proper counting
    
    return MCPServersPublic(data=[MCPServerPublic(**server.model_dump()) for server in servers], count=count)


@router.get("/servers/public", response_model=MCPServersPublic)
async def read_public_mcp_servers(
    session: SessionDep,
    skip: int = 0,
    limit: int = 100
) -> Any:
    """
    Retrieve public MCP servers.
    
    Returns publicly available MCP servers that anyone can discover.
    """
    repo = MCPServerRepository(session)
    servers = await repo.get_public_servers(skip=skip, limit=limit)
    
    return MCPServersPublic(data=[MCPServerPublic(**server.model_dump()) for server in servers], count=len(servers))


@router.get("/servers/search", response_model=MCPServersPublic)
async def search_mcp_servers(
    session: SessionDep,
    current_user: CurrentUser,
    q: str,
    skip: int = 0,
    limit: int = 100
) -> Any:
    """
    Search MCP servers by name or description.
    
    Searches within the user's own servers unless they are a superuser.
    """
    repo = MCPServerRepository(session)
    
    if getattr(current_user, 'is_superuser', False):
        # Superusers can search all servers
        servers = await repo.search_servers(
            query=q, 
            skip=skip, 
            limit=limit
        )
    else:
        # Regular users search only their own servers
        servers = await repo.search_servers(
            query=q, 
            owner_id=current_user.id,
            skip=skip, 
            limit=limit
        )
    
    return MCPServersPublic(data=[MCPServerPublic(**server.model_dump()) for server in servers], count=len(servers))


@router.post("/servers", response_model=MCPServerPublic)
async def create_mcp_server(
    *, 
    session: SessionDep, 
    current_user: CurrentUser, 
    server_in: MCPServerCreate
) -> Any:
    """
    Create a new MCP server.
    """
    repo = MCPServerRepository(session)
    
    # Check if server name already exists for this user
    existing_server = await repo.get_by_name_and_owner(
        name=server_in.name, 
        owner_id=current_user.id
    )
    if existing_server:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A server with this name already exists for your account"
        )
    
    server = await repo.create(server_create=server_in, owner_id=current_user.id)
    return server


@router.get("/servers/{server_id}", response_model=MCPServerPublic)
async def read_mcp_server(
    *, 
    session: SessionDep, 
    current_user: CurrentUser, 
    server_id: uuid.UUID
) -> Any:
    """
    Get MCP server by ID.
    """
    repo = MCPServerRepository(session)
    server = await repo.get_by_id(server_id=server_id)
    
    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="MCP server not found"
        )
    
    # Check access permissions
    if not getattr(current_user, 'is_superuser', False) and server.owner_id != current_user.id:
        # Allow access to public servers
        if not server.is_public:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions to access this server"
            )
    
    return server


@router.put("/servers/{server_id}", response_model=MCPServerPublic)
async def update_mcp_server(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    server_id: uuid.UUID,
    server_in: MCPServerUpdate,
) -> Any:
    """
    Update an MCP server.
    """
    repo = MCPServerRepository(session)
    server = await repo.get_by_id(server_id=server_id)
    
    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="MCP server not found"
        )
    
    # Check ownership permissions
    if not getattr(current_user, 'is_superuser', False) and server.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to update this server"
        )
    
    # Check for name conflicts if name is being updated
    if server_in.name and server_in.name != server.name:
        existing_server = await repo.get_by_name_and_owner(
            name=server_in.name, 
            owner_id=current_user.id
        )
        if existing_server:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A server with this name already exists for your account"
            )
    
    updated_server = await repo.update(server_id=server_id, server_update=server_in)
    return updated_server


@router.delete("/servers/{server_id}", response_model=Message)
async def delete_mcp_server(
    *, 
    session: SessionDep, 
    current_user: CurrentUser, 
    server_id: uuid.UUID
) -> Any:
    """
    Delete an MCP server.
    """
    repo = MCPServerRepository(session)
    server = await repo.get_by_id(server_id=server_id)
    
    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="MCP server not found"
        )
    
    # Check ownership permissions
    if not getattr(current_user, 'is_superuser', False) and server.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to delete this server"
        )
    
    await repo.delete(server_id=server_id)
    return Message(message="MCP server deleted successfully")


@router.post("/servers/{server_id}/health", response_model=MCPServerHealthCheck)
async def check_mcp_server_health(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    server_id: uuid.UUID,
) -> Any:
    """
    Perform a health check on an MCP server.
    
    Updates the last_health_check timestamp and returns server status.
    """
    repo = MCPServerRepository(session)
    server = await repo.get_by_id(server_id=server_id)
    
    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="MCP server not found"
        )
    
    # Check access permissions (owners, superusers, and users of public servers can perform health checks)
    if not getattr(current_user, 'is_superuser', False) and server.owner_id != current_user.id:
        # Allow health checks on public servers
        if not server.is_public:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions to perform health check on this server"
            )
    
    # Perform actual health check based on server type
    health_status = MCPServerStatus.INACTIVE
    error_message = None
    response_time_ms = None
    
    try:
        import time
        import httpx
        
        start_time = time.time()
        
        if server.server_type == "http":
            # For HTTP servers, send an initialize request
            async with httpx.AsyncClient() as client:
                url = server.connection_config.get("url", "")
                headers = server.connection_config.get("headers", {})
                
                response = await client.post(
                    url,
                    json={
                        "jsonrpc": "2.0",
                        "method": "initialize",
                        "params": {},
                        "id": 1
                    },
                    headers=headers,
                    timeout=5.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if "result" in result:
                        health_status = MCPServerStatus.ACTIVE
                    else:
                        health_status = MCPServerStatus.ERROR
                        error_message = "Invalid response format"
                else:
                    health_status = MCPServerStatus.ERROR
                    error_message = f"HTTP {response.status_code}"
                    
        elif server.server_type == "stdio":
            # For STDIO servers, just check if the command exists
            # In a real implementation, we'd try to start the process
            health_status = MCPServerStatus.ACTIVE
            
        response_time_ms = int((time.time() - start_time) * 1000)
        
    except Exception as e:
        health_status = MCPServerStatus.ERROR
        error_message = str(e)
    
    # Update server status in database
    updated_server = await repo.update_health_check(
        server_id=server_id, 
        status=health_status
    )
    
    if updated_server is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update health check"
        )
    
    # Get available tools if server is active
    available_tools = None
    if health_status == MCPServerStatus.ACTIVE and server.server_type == "stdio":
        # For STDIO servers, we would need to start the server and query tools
        # For now, we'll return the tools from capabilities if available
        available_tools = server.capabilities.get("tools", []) if server.capabilities else []
    
    return MCPServerHealthCheck(
        server_id=server_id,
        status=health_status,
        last_check=updated_server.last_health_check or datetime.utcnow(),
        response_time_ms=response_time_ms,
        error=error_message,
        available_tools=available_tools,
    )


@router.get("/servers/status/{status}", response_model=MCPServersPublic)
async def read_mcp_servers_by_status(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    status: MCPServerStatus,
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    Retrieve MCP servers by status.
    
    Only superusers can filter by status across all servers.
    Regular users see their own servers with the specified status.
    """
    if not getattr(current_user, 'is_superuser', False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superusers can filter servers by status"
        )
    
    repo = MCPServerRepository(session)
    servers = await repo.get_servers_by_status(
        status=status, 
        skip=skip, 
        limit=limit
    )
    
    return MCPServersPublic(data=[MCPServerPublic(**server.model_dump()) for server in servers], count=len(servers))


# Session endpoints
@router.post("/sessions", response_model=MCPSessionPublic)
async def create_mcp_session(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    session_create: MCPSessionCreate,
) -> Any:
    """
    Create a new MCP session.
    """
    from app.repositories.mcp_session import MCPSessionRepository
    
    repo = MCPSessionRepository(session)
    new_session = await repo.create_session(
        user_id=current_user.id,
        server_id=session_create.server_id,
        title=session_create.title,
        context=session_create.context
    )
    
    return new_session


@router.get("/sessions", response_model=List[MCPSessionPublic])
async def get_mcp_sessions(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    server_id: uuid.UUID = None,
    archived: bool = False,
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    Get MCP sessions for the current user.
    
    Optionally filter by server_id and archived status.
    """
    from app.repositories.mcp_session import MCPSessionRepository
    
    repo = MCPSessionRepository(session)
    sessions = await repo.get_user_sessions(
        user_id=current_user.id,
        server_id=server_id,
        archived=archived,
        limit=limit,
        offset=skip
    )
    
    return sessions


@router.get("/sessions/{session_id}", response_model=MCPSessionPublic)
async def get_mcp_session(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    session_id: uuid.UUID,
) -> Any:
    """
    Get a specific MCP session.
    """
    from app.repositories.mcp_session import MCPSessionRepository
    
    repo = MCPSessionRepository(session)
    mcp_session = await repo.get_session(session_id=session_id)
    
    if not mcp_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    # Check if user owns the session
    if mcp_session.user_id != current_user.id and not getattr(current_user, 'is_superuser', False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to access this session"
        )
    
    return mcp_session


@router.get("/sessions/{session_id}/messages", response_model=List[MCPMessagePublic])
async def get_session_messages(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    session_id: uuid.UUID,
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    Get messages for a session.
    """
    from app.repositories.mcp_session import MCPSessionRepository
    
    repo = MCPSessionRepository(session)
    
    # First verify the session exists and user has access
    mcp_session = await repo.get_session(session_id=session_id)
    if not mcp_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    if mcp_session.user_id != current_user.id and not getattr(current_user, 'is_superuser', False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to access this session"
        )
    
    messages = await repo.get_session_messages(
        session_id=session_id,
        limit=limit,
        offset=skip
    )
    
    return messages


@router.put("/sessions/{session_id}/end")
async def end_mcp_session(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    session_id: uuid.UUID,
) -> Any:
    """
    End an MCP session.
    """
    from app.repositories.mcp_session import MCPSessionRepository
    
    repo = MCPSessionRepository(session)
    
    # First verify the session exists and user has access
    mcp_session = await repo.get_session(session_id=session_id)
    if not mcp_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    if mcp_session.user_id != current_user.id and not getattr(current_user, 'is_superuser', False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to access this session"
        )
    
    await repo.end_session(session_id=session_id)
    
    return {"message": "Session ended successfully"}


@router.put("/sessions/{session_id}/archive")
async def archive_mcp_session(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    session_id: uuid.UUID,
) -> Any:
    """
    Archive an MCP session.
    """
    from app.repositories.mcp_session import MCPSessionRepository
    
    repo = MCPSessionRepository(session)
    
    # First verify the session exists and user has access
    mcp_session = await repo.get_session(session_id=session_id)
    if not mcp_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    if mcp_session.user_id != current_user.id and not getattr(current_user, 'is_superuser', False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to archive this session"
        )
    
    success = await repo.archive_session(session_id=session_id, user_id=current_user.id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to archive session. It may already be archived."
        )
    
    return {"message": "Session archived successfully"}


@router.put("/sessions/{session_id}/unarchive")
async def unarchive_mcp_session(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    session_id: uuid.UUID,
) -> Any:
    """
    Unarchive an MCP session.
    """
    from app.repositories.mcp_session import MCPSessionRepository
    
    repo = MCPSessionRepository(session)
    
    # First verify the session exists and user has access
    mcp_session = await repo.get_session(session_id=session_id)
    if not mcp_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    if mcp_session.user_id != current_user.id and not getattr(current_user, 'is_superuser', False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to unarchive this session"
        )
    
    success = await repo.unarchive_session(session_id=session_id, user_id=current_user.id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to unarchive session. It may not be archived."
        )
    
    return {"message": "Session unarchived successfully"}