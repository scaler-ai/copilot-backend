"""
Tests for MCP Server Repository.

This module tests the MCPServerRepository for all CRUD operations
and business logic methods.
"""

import uuid
import pytest
from datetime import datetime
from typing import Any

from app.repositories.mcp_server import MCPServerRepository
from app.schemas.mcp import MCPServerCreate, MCPServerUpdate, MCPServerType, MCPServerStatus


@pytest.fixture
async def test_user_id() -> uuid.UUID:
    """Get a test user ID from the database."""
    import asyncpg
    from app.core.config import settings
    
    conn = await asyncpg.connect(
        host=settings.POSTGRES_SERVER,
        port=settings.POSTGRES_PORT,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        database=settings.POSTGRES_DB
    )
    
    try:
        user_id = await conn.fetchval("SELECT id FROM users LIMIT 1")
        if not user_id:
            pytest.skip("No test users available")
        return uuid.UUID(str(user_id))
    finally:
        await conn.close()


@pytest.fixture
def sample_server_create() -> MCPServerCreate:
    """Create a sample MCPServerCreate instance."""
    return MCPServerCreate(
        name="test-server",
        description="A test MCP server",
        server_type=MCPServerType.HTTP,
        connection_config={"url": "http://localhost:3000", "timeout": 30},
        is_public=False,
        version="1.0.0",
        capabilities={"tools": ["test_tool"], "prompts": []}
    )


@pytest.fixture
def mcp_server_repo(session: Any) -> MCPServerRepository:
    """Create an MCPServerRepository instance."""
    return MCPServerRepository(session)


@pytest.mark.asyncio
async def test_create_mcp_server(mcp_server_repo: MCPServerRepository, sample_server_create: MCPServerCreate, test_user_id: uuid.UUID) -> None:
    """Test creating an MCP server."""
    # Create server
    server = await mcp_server_repo.create(
        server_create=sample_server_create,
        owner_id=test_user_id
    )
    
    # Verify creation
    assert server is not None
    assert server.name == sample_server_create.name
    assert server.description == sample_server_create.description
    assert server.server_type == sample_server_create.server_type
    assert server.owner_id == test_user_id
    assert server.status == MCPServerStatus.INACTIVE  # Default status
    assert server.connection_config == sample_server_create.connection_config
    assert server.capabilities == sample_server_create.capabilities
    assert isinstance(server.id, uuid.UUID)
    assert isinstance(server.created_at, datetime)
    assert isinstance(server.updated_at, datetime)
    
    # Clean up
    await mcp_server_repo.delete(server_id=server.id)


@pytest.mark.asyncio
async def test_get_server_by_id(mcp_server_repo: MCPServerRepository, sample_server_create: MCPServerCreate, test_user_id: uuid.UUID) -> None:
    """Test getting an MCP server by ID."""
    # Create server
    created_server = await mcp_server_repo.create(
        server_create=sample_server_create,
        owner_id=test_user_id
    )
    
    # Get server by ID
    retrieved_server = await mcp_server_repo.get_by_id(server_id=created_server.id)
    
    # Verify retrieval
    assert retrieved_server is not None
    assert retrieved_server.id == created_server.id
    assert retrieved_server.name == created_server.name
    assert retrieved_server.owner_id == test_user_id
    
    # Test non-existent server
    non_existent_server = await mcp_server_repo.get_by_id(server_id=uuid.uuid4())
    assert non_existent_server is None
    
    # Clean up
    await mcp_server_repo.delete(server_id=created_server.id)


@pytest.mark.asyncio
async def test_update_mcp_server(mcp_server_repo: MCPServerRepository, sample_server_create: MCPServerCreate, test_user_id: uuid.UUID) -> None:
    """Test updating an MCP server."""
    # Create server
    created_server = await mcp_server_repo.create(
        server_create=sample_server_create,
        owner_id=test_user_id
    )
    
    # Update server
    server_update = MCPServerUpdate(  # type: ignore[call-arg]
        description="Updated description",
        status=MCPServerStatus.ACTIVE,
        version="2.0.0"
    )
    
    updated_server = await mcp_server_repo.update(
        server_id=created_server.id,
        server_update=server_update
    )
    
    # Verify update
    assert updated_server is not None
    assert updated_server.id == created_server.id
    assert updated_server.description == "Updated description"
    assert updated_server.status == MCPServerStatus.ACTIVE
    assert updated_server.version == "2.0.0"
    assert updated_server.name == created_server.name  # Unchanged
    assert updated_server.updated_at > created_server.updated_at
    
    # Clean up
    await mcp_server_repo.delete(server_id=created_server.id)


@pytest.mark.asyncio
async def test_delete_mcp_server(mcp_server_repo: MCPServerRepository, sample_server_create: MCPServerCreate, test_user_id: uuid.UUID) -> None:
    """Test deleting an MCP server."""
    # Create server
    created_server = await mcp_server_repo.create(
        server_create=sample_server_create,
        owner_id=test_user_id
    )
    
    # Verify server exists
    retrieved_server = await mcp_server_repo.get_by_id(server_id=created_server.id)
    assert retrieved_server is not None
    
    # Delete server
    delete_result = await mcp_server_repo.delete(server_id=created_server.id)
    assert delete_result is True
    
    # Verify server is deleted
    deleted_server = await mcp_server_repo.get_by_id(server_id=created_server.id)
    assert deleted_server is None


@pytest.mark.asyncio
async def test_unique_constraint(mcp_server_repo: MCPServerRepository, sample_server_create: MCPServerCreate, test_user_id: uuid.UUID) -> None:
    """Test that the unique constraint on (name, owner_id) is enforced."""
    # Create first server with unique name
    unique_name = f"unique-test-{uuid.uuid4().hex[:8]}"
    server_create = MCPServerCreate(
        name=unique_name,
        description="Test server for unique constraint",
        server_type=MCPServerType.HTTP,
        connection_config={"url": "http://localhost:3000"},
        version="1.0.0"
    )
    
    first_server = await mcp_server_repo.create(
        server_create=server_create,
        owner_id=test_user_id
    )
    
    # Try to create second server with same name and owner
    try:
        await mcp_server_repo.create(
            server_create=server_create,
            owner_id=test_user_id
        )
        # If we get here, the constraint wasn't enforced
        assert False, "Expected unique constraint violation"
    except Exception as e:
        # Expected - unique constraint should be violated
        assert "unique" in str(e).lower() or "duplicate" in str(e).lower()
    
    # Clean up
    await mcp_server_repo.delete(server_id=first_server.id)