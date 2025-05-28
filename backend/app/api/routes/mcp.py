"""
MCP (Model Context Protocol) API endpoints.

This module provides REST API endpoints for managing MCP servers,
tools, sessions, and protocol interactions.
"""

import uuid
from typing import Any

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
)
from app.models import Message

router = APIRouter(prefix="/mcp", tags=["mcp"])


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
    
    if current_user.is_superuser:
        # Superusers can see all servers
        servers = await repo.get_multi(skip=skip, limit=limit)
        count = await repo.count()
    else:
        # Regular users see only their own servers
        servers = await repo.get_by_owner(owner_id=current_user.id, skip=skip, limit=limit)
        # TODO: Add count method for owner-specific queries
        count = len(servers)  # Temporary - should implement proper counting
    
    return MCPServersPublic(data=servers, count=count)


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
    
    return MCPServersPublic(data=servers, count=len(servers))


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
    
    if current_user.is_superuser:
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
    
    return MCPServersPublic(data=servers, count=len(servers))


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
    if not current_user.is_superuser and server.owner_id != current_user.id:
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
    if not current_user.is_superuser and server.owner_id != current_user.id:
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
    if not current_user.is_superuser and server.owner_id != current_user.id:
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
    
    # Check access permissions (owners and superusers can perform health checks)
    if not current_user.is_superuser and server.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to perform health check on this server"
        )
    
    # Update health check timestamp
    updated_server = await repo.update_health_check(server_id=server_id)
    
    # TODO: Implement actual health check logic
    # For now, return basic health check info
    return MCPServerHealthCheck(
        server_id=server_id,
        status=updated_server.status,
        last_check=updated_server.last_health_check,
        response_time_ms=None,  # TODO: Implement actual ping
        error=None,
        available_tools=None,  # TODO: Query actual tools
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
    if not current_user.is_superuser:
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
    
    return MCPServersPublic(data=servers, count=len(servers))