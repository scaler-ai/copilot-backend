"""
Repository for MCP Server database operations.

This module provides database operations for MCP servers using direct SQL
queries instead of SQLModel table models to avoid metadata conflicts.
"""

import uuid
import json
from datetime import datetime
from typing import List, Optional, Dict, Any

import asyncpg
from sqlmodel import Session

from app.core.config import settings
# from app.repositories.base import BaseRepository, JsonFieldMixin
from app.schemas.mcp import (
    MCPServerCreate,
    MCPServerUpdate,
    MCPServerInDB,
    MCPServerType,
    MCPServerStatus
)


class MCPServerRepository:
    """Repository for MCP Server database operations."""
    
    def __init__(self, session: Session):
        self.session = session
    
    async def _get_connection(self) -> asyncpg.Connection:
        """Get a database connection."""
        return await asyncpg.connect(
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD,
            database=settings.POSTGRES_DB,
            host=settings.POSTGRES_SERVER,
            port=settings.POSTGRES_PORT,
        )
    
    def _parse_server_data(self, row: asyncpg.Record) -> MCPServerInDB:
        """Parse a database row into an MCPServerInDB object."""
        data = dict(row)
        
        # Parse JSON fields
        json_fields = ["connection_config", "allowed_users", "allowed_roles", "capabilities"]
        for field in json_fields:
            if data.get(field) is not None:
                if isinstance(data[field], str):
                    data[field] = json.loads(data[field])
        
        return MCPServerInDB(**data)

    async def create(self, *, server_create: MCPServerCreate, owner_id: uuid.UUID) -> MCPServerInDB:
        """Create a new MCP server."""
        conn = await self._get_connection()
        try:
            server_id = uuid.uuid4()
            now = datetime.utcnow()
            
            # Insert the server
            await conn.execute("""
                INSERT INTO mcp_servers (
                    id, created_at, updated_at, name, description, server_type, 
                    status, connection_config, owner_id, is_public, allowed_users, 
                    allowed_roles, version, capabilities
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
            """, 
                server_id, now, now,
                server_create.name,
                server_create.description,
                server_create.server_type.value,
                server_create.status.value if server_create.status else MCPServerStatus.INACTIVE.value,
                json.dumps(server_create.connection_config),
                owner_id,
                server_create.is_public or False,
                json.dumps(server_create.allowed_users or []),
                json.dumps(server_create.allowed_roles or []),
                server_create.version,
                json.dumps(server_create.capabilities or {})
            )
            
            # Fetch and return the created server
            result = await self.get_by_id(server_id=server_id)
            if result is None:
                raise RuntimeError(f"Failed to retrieve created server {server_id}")
            return result
            
        finally:
            await conn.close()

    async def get_by_id(self, *, server_id: uuid.UUID) -> Optional[MCPServerInDB]:
        """Get MCP server by ID."""
        conn = await self._get_connection()
        try:
            result = await conn.fetchrow(
                "SELECT * FROM mcp_servers WHERE id = $1",
                server_id
            )
            
            if not result:
                return None
                
            return self._parse_server_data(result)
            
        finally:
            await conn.close()

    async def get_by_name_and_owner(self, *, name: str, owner_id: uuid.UUID) -> Optional[MCPServerInDB]:
        """Get MCP server by name and owner (unique constraint)."""
        conn = await self._get_connection()
        try:
            result = await conn.fetchrow(
                "SELECT * FROM mcp_servers WHERE name = $1 AND owner_id = $2",
                name, owner_id
            )
            
            if not result:
                return None
                
            return self._parse_server_data(result)
            
        finally:
            await conn.close()

    async def get_by_owner(self, *, owner_id: uuid.UUID, skip: int = 0, limit: int = 100) -> List[MCPServerInDB]:
        """Get MCP servers by owner with pagination."""
        conn = await self._get_connection()
        try:
            results = await conn.fetch("""
                SELECT * FROM mcp_servers 
                WHERE owner_id = $1 
                ORDER BY created_at DESC 
                OFFSET $2 LIMIT $3
            """, owner_id, skip, limit)
            
            return [self._parse_server_data(row) for row in results]
            
        finally:
            await conn.close()

    async def get_public_servers(self, *, skip: int = 0, limit: int = 100) -> List[MCPServerInDB]:
        """Get public MCP servers with pagination."""
        conn = await self._get_connection()
        try:
            results = await conn.fetch("""
                SELECT * FROM mcp_servers 
                WHERE is_public = true AND status = 'active'
                ORDER BY created_at DESC 
                OFFSET $1 LIMIT $2
            """, skip, limit)
            
            return [self._parse_server_data(row) for row in results]
            
        finally:
            await conn.close()

    async def update(self, *, server_id: uuid.UUID, server_update: MCPServerUpdate) -> Optional[MCPServerInDB]:
        """Update an MCP server."""
        conn = await self._get_connection()
        try:
            # Build dynamic update query
            update_data = server_update.model_dump(exclude_unset=True)
            if not update_data:
                return await self.get_by_id(server_id=server_id)
            
            set_clauses = []
            values: List[Any] = [server_id]  # $1 is always server_id
            param_index = 2
            
            for field, value in update_data.items():
                if field in ["server_type", "status"] and hasattr(value, "value"):
                    value = value.value
                elif field in ["connection_config", "capabilities"] and isinstance(value, dict):
                    value = json.dumps(value)
                elif field in ["allowed_users", "allowed_roles"] and isinstance(value, list):
                    value = json.dumps(value)
                set_clauses.append(f"{field} = ${param_index}")
                values.append(value)
                param_index += 1
            
            # Always update updated_at
            set_clauses.append(f"updated_at = ${param_index}")
            values.append(datetime.utcnow())
            
            query = f"""
                UPDATE mcp_servers 
                SET {', '.join(set_clauses)}
                WHERE id = $1
            """
            
            await conn.execute(query, *values)
            
            # Return updated server
            return await self.get_by_id(server_id=server_id)
            
        finally:
            await conn.close()

    async def delete(self, *, server_id: uuid.UUID) -> bool:
        """Delete an MCP server."""
        conn = await self._get_connection()
        try:
            result = await conn.execute(
                "DELETE FROM mcp_servers WHERE id = $1",
                server_id
            )
            
            # Check if any rows were affected
            return "DELETE 1" in result
            
        finally:
            await conn.close()

    async def update_health_check(self, *, server_id: uuid.UUID) -> Optional[MCPServerInDB]:
        """Update the last health check timestamp for a server."""
        conn = await self._get_connection()
        try:
            await conn.execute("""
                UPDATE mcp_servers 
                SET last_health_check = NOW(), updated_at = NOW()
                WHERE id = $1
            """, server_id)
            
            return await self.get_by_id(server_id=server_id)
            
        finally:
            await conn.close()

    async def get_servers_by_status(self, *, status: MCPServerStatus, skip: int = 0, limit: int = 100) -> List[MCPServerInDB]:
        """Get MCP servers by status with pagination."""
        conn = await self._get_connection()
        try:
            results = await conn.fetch("""
                SELECT * FROM mcp_servers 
                WHERE status = $1 
                ORDER BY created_at DESC 
                OFFSET $2 LIMIT $3
            """, status.value, skip, limit)
            
            return [self._parse_server_data(row) for row in results]
            
        finally:
            await conn.close()

    async def search_servers(self, *, query: str, owner_id: Optional[uuid.UUID] = None, skip: int = 0, limit: int = 100) -> List[MCPServerInDB]:
        """Search MCP servers by name or description. Empty query returns all servers."""
        conn = await self._get_connection()
        try:
            if query.strip() == "":
                # Empty query - return all servers
                if owner_id:
                    where_clause = "WHERE owner_id = $1"
                    params = [owner_id, skip, limit]
                    offset_param = "$2"
                    limit_param = "$3"
                else:
                    where_clause = ""
                    params = [skip, limit]
                    offset_param = "$1"
                    limit_param = "$2"
            else:
                # Search query
                where_clause = "WHERE (name ILIKE $1 OR description ILIKE $1)"
                params: List[Any] = [f"%{query}%"]
                
                if owner_id:
                    where_clause += " AND owner_id = $2"
                    params.append(owner_id)
                    offset_param = "$3"
                    limit_param = "$4"
                else:
                    offset_param = "$2"
                    limit_param = "$3"
                
                params.extend([skip, limit])
            
            sql = f"""
                SELECT * FROM mcp_servers 
                {where_clause}
                ORDER BY created_at DESC 
                OFFSET {offset_param} LIMIT {limit_param}
            """
            
            results = await conn.fetch(sql, *params)
            
            return [self._parse_server_data(row) for row in results]
            
        finally:
            await conn.close()


# Convenience function for getting repository instance
def get_mcp_server_repository(session: Session) -> MCPServerRepository:
    """Get an MCPServerRepository instance."""
    return MCPServerRepository(session)