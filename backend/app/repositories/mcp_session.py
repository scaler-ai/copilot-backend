"""
Repository for MCP Session database operations.
"""

import uuid
import json
from datetime import datetime
from typing import List, Optional, Dict, Any

import asyncpg
from sqlmodel import Session

from app.core.config import settings
from app.schemas.mcp import (
    MCPSessionCreate,
    MCPSessionUpdate,
    MCPSessionPublic,
    MCPSessionStatus,
    MCPMessageCreate,
    MCPMessagePublic,
    MCPMessageRole,
)


class MCPSessionRepository:
    """Repository for MCP Session database operations."""
    
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
    
    async def create_session(
        self, 
        *, 
        user_id: uuid.UUID,
        server_id: uuid.UUID,
        title: Optional[str] = None,
        context: Dict[str, Any] = None
    ) -> MCPSessionPublic:
        """Create a new MCP session."""
        conn = await self._get_connection()
        try:
            session_id = uuid.uuid4()
            now = datetime.utcnow()
            
            await conn.execute("""
                INSERT INTO mcp_sessions (
                    id, created_at, updated_at, user_id, server_id,
                    title, status, context, metadata, started_at, last_activity
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            """,
                session_id, now, now, user_id, server_id,
                title or f"Session {now.strftime('%Y-%m-%d %H:%M')}",
                MCPSessionStatus.ACTIVE.value,
                json.dumps(context or {}),
                json.dumps({}),
                now, now
            )
            
            # Return the created session
            result = await conn.fetchrow(
                "SELECT * FROM mcp_sessions WHERE id = $1",
                session_id
            )
            
            return self._parse_session_data(result)
            
        finally:
            await conn.close()
    
    async def get_session(self, *, session_id: uuid.UUID) -> Optional[MCPSessionPublic]:
        """Get a session by ID."""
        conn = await self._get_connection()
        try:
            result = await conn.fetchrow(
                "SELECT * FROM mcp_sessions WHERE id = $1",
                session_id
            )
            
            if not result:
                return None
                
            return self._parse_session_data(result)
            
        finally:
            await conn.close()
    
    async def update_session_activity(self, *, session_id: uuid.UUID):
        """Update the last activity timestamp for a session."""
        conn = await self._get_connection()
        try:
            await conn.execute("""
                UPDATE mcp_sessions 
                SET last_activity = NOW(), updated_at = NOW()
                WHERE id = $1
            """, session_id)
            
        finally:
            await conn.close()
    
    async def end_session(
        self, 
        *, 
        session_id: uuid.UUID,
        status: MCPSessionStatus = MCPSessionStatus.COMPLETED
    ):
        """End a session with the given status."""
        conn = await self._get_connection()
        try:
            now = datetime.utcnow()
            await conn.execute("""
                UPDATE mcp_sessions 
                SET status = $1, ended_at = $2, updated_at = $3
                WHERE id = $4
            """, status.value, now, now, session_id)
            
        finally:
            await conn.close()
    
    async def archive_session(
        self,
        *,
        session_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> bool:
        """Archive a session."""
        conn = await self._get_connection()
        try:
            now = datetime.utcnow()
            result = await conn.execute("""
                UPDATE mcp_sessions 
                SET archived = true, archived_at = $1, updated_at = $1
                WHERE id = $2 AND user_id = $3 AND archived = false
            """, now, session_id, user_id)
            
            return result.split()[-1] == '1'
            
        finally:
            await conn.close()
    
    async def unarchive_session(
        self,
        *,
        session_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> bool:
        """Unarchive a session."""
        conn = await self._get_connection()
        try:
            now = datetime.utcnow()
            result = await conn.execute("""
                UPDATE mcp_sessions 
                SET archived = false, archived_at = NULL, updated_at = $1
                WHERE id = $2 AND user_id = $3 AND archived = true
            """, now, session_id, user_id)
            
            return result.split()[-1] == '1'
            
        finally:
            await conn.close()
    
    async def add_message(
        self,
        *,
        session_id: uuid.UUID,
        role: MCPMessageRole,
        content: str,
        tool_call_id: Optional[str] = None,
        tool_name: Optional[str] = None,
        metadata: Dict[str, Any] = None
    ) -> MCPMessagePublic:
        """Add a message to a session."""
        conn = await self._get_connection()
        try:
            message_id = uuid.uuid4()
            now = datetime.utcnow()
            
            await conn.execute("""
                INSERT INTO mcp_messages (
                    id, created_at, updated_at, session_id, role,
                    content, tool_call_id, tool_name, metadata
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """,
                message_id, now, now, session_id, role.value,
                content, tool_call_id, tool_name,
                json.dumps(metadata or {})
            )
            
            # Update session activity
            await self.update_session_activity(session_id=session_id)
            
            # Return the created message
            result = await conn.fetchrow(
                "SELECT * FROM mcp_messages WHERE id = $1",
                message_id
            )
            
            return self._parse_message_data(result)
            
        finally:
            await conn.close()
    
    async def get_session_messages(
        self,
        *,
        session_id: uuid.UUID,
        limit: int = 100,
        offset: int = 0
    ) -> List[MCPMessagePublic]:
        """Get messages for a session."""
        conn = await self._get_connection()
        try:
            results = await conn.fetch("""
                SELECT * FROM mcp_messages 
                WHERE session_id = $1
                ORDER BY created_at ASC
                LIMIT $2 OFFSET $3
            """, session_id, limit, offset)
            
            return [self._parse_message_data(row) for row in results]
            
        finally:
            await conn.close()
    
    async def get_user_sessions(
        self,
        *,
        user_id: uuid.UUID,
        server_id: Optional[uuid.UUID] = None,
        status: Optional[MCPSessionStatus] = None,
        archived: Optional[bool] = False,
        limit: int = 100,
        offset: int = 0
    ) -> List[MCPSessionPublic]:
        """Get sessions for a user."""
        conn = await self._get_connection()
        try:
            # Build query based on filters
            query = "SELECT * FROM mcp_sessions WHERE user_id = $1"
            params = [user_id]
            param_idx = 2
            
            if server_id:
                query += f" AND server_id = ${param_idx}"
                params.append(server_id)
                param_idx += 1
            
            if status:
                query += f" AND status = ${param_idx}"
                params.append(status.value)
                param_idx += 1
            
            # Add archived filter
            query += f" AND archived = ${param_idx}"
            params.append(archived)
            param_idx += 1
            
            query += f" ORDER BY created_at DESC LIMIT ${param_idx} OFFSET ${param_idx + 1}"
            params.extend([limit, offset])
            
            results = await conn.fetch(query, *params)
            
            return [self._parse_session_data(row) for row in results]
            
        finally:
            await conn.close()
    
    def _parse_session_data(self, row: asyncpg.Record) -> MCPSessionPublic:
        """Parse a database row into a session object."""
        data = dict(row)
        
        # Parse JSON fields
        for field in ["context", "metadata"]:
            if data.get(field) is not None and isinstance(data[field], str):
                data[field] = json.loads(data[field])
        
        return MCPSessionPublic(**data)
    
    def _parse_message_data(self, row: asyncpg.Record) -> MCPMessagePublic:
        """Parse a database row into a message object."""
        data = dict(row)
        
        # Parse JSON fields
        if data.get("metadata") is not None and isinstance(data["metadata"], str):
            data["metadata"] = json.loads(data["metadata"])
        
        return MCPMessagePublic(**data)


# Convenience function
def get_mcp_session_repository(session: Session) -> MCPSessionRepository:
    """Get an MCPSessionRepository instance."""
    return MCPSessionRepository(session)