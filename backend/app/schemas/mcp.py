import enum
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field


# Enum definitions for MCP schemas
class MCPServerType(str, enum.Enum):
    STDIO = "stdio"
    HTTP = "http"
    WEBSOCKET = "websocket"


class MCPServerStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class MCPSessionStatus(str, enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ERROR = "error"
    TIMEOUT = "timeout"


class MCPMessageRole(str, enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class MCPToolExecutionStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"


# MCP Server Schemas
class MCPServerBase(BaseModel):
    """Base schema for MCP Server"""
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    server_type: MCPServerType
    connection_config: Dict[str, Any] = Field(default_factory=dict)
    is_public: bool = False
    allowed_users: List[UUID] = Field(default_factory=list)
    allowed_roles: List[str] = Field(default_factory=list)
    version: Optional[str] = Field(None, max_length=50)
    capabilities: Dict[str, Any] = Field(default_factory=dict)


class MCPServerCreate(MCPServerBase):
    """Schema for creating an MCP Server"""
    status: Optional[MCPServerStatus] = None


class MCPServerUpdate(BaseModel):
    """Schema for updating an MCP Server"""
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    status: Optional[MCPServerStatus] = None
    connection_config: Optional[Dict[str, Any]] = None
    is_public: Optional[bool] = None
    allowed_users: Optional[List[UUID]] = None
    allowed_roles: Optional[List[str]] = None
    version: Optional[str] = Field(None, max_length=50)
    capabilities: Optional[Dict[str, Any]] = None


class MCPServerInDB(MCPServerBase):
    """Database schema for MCP Server (internal use)"""
    id: UUID
    status: MCPServerStatus
    owner_id: UUID
    last_health_check: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MCPServerPublic(MCPServerBase):
    """Public schema for MCP Server"""
    id: UUID
    status: MCPServerStatus
    owner_id: UUID
    last_health_check: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MCPServersPublic(BaseModel):
    """Schema for list of MCP Servers"""
    data: List[MCPServerPublic]
    count: int


# MCP Tool Schemas
class MCPTool(BaseModel):
    """Schema for MCP Tool definition (from server)"""
    name: str
    description: Optional[str] = None
    inputSchema: Optional[Dict[str, Any]] = None


class MCPToolBase(BaseModel):
    """Base schema for MCP Tool"""
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    input_schema: Dict[str, Any]
    category: Optional[str] = Field(None, max_length=100)
    tags: List[str] = Field(default_factory=list)


class MCPToolPublic(MCPToolBase):
    """Public schema for MCP Tool"""
    id: UUID
    server_id: UUID
    usage_count: int = 0
    last_used: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MCPToolsPublic(BaseModel):
    """Schema for list of MCP Tools"""
    data: List[MCPToolPublic]
    count: int


# MCP Session Schemas
class MCPSessionBase(BaseModel):
    """Base schema for MCP Session"""
    server_id: UUID
    title: Optional[str] = Field(None, max_length=255)
    context: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MCPSessionCreate(MCPSessionBase):
    """Schema for creating an MCP Session"""
    pass


class MCPSessionUpdate(BaseModel):
    """Schema for updating an MCP Session"""
    title: Optional[str] = Field(None, max_length=255)
    status: Optional[MCPSessionStatus] = None
    context: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    archived: Optional[bool] = None


class MCPSessionPublic(MCPSessionBase):
    """Public schema for MCP Session"""
    id: UUID
    user_id: UUID
    status: MCPSessionStatus
    started_at: datetime
    ended_at: Optional[datetime] = None
    last_activity: datetime
    archived: bool = False
    archived_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MCPSessionsPublic(BaseModel):
    """Schema for list of MCP Sessions"""
    data: List[MCPSessionPublic]
    count: int


# MCP Message Schemas
class MCPMessageBase(BaseModel):
    """Base schema for MCP Message"""
    role: MCPMessageRole
    content: str
    tool_call_id: Optional[str] = Field(None, max_length=255)
    tool_name: Optional[str] = Field(None, max_length=255)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MCPMessageCreate(MCPMessageBase):
    """Schema for creating an MCP Message"""
    session_id: UUID


class MCPMessagePublic(MCPMessageBase):
    """Public schema for MCP Message"""
    id: UUID
    session_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MCPMessagesPublic(BaseModel):
    """Schema for list of MCP Messages"""
    data: List[MCPMessagePublic]
    count: int


# MCP Tool Execution Schemas
class MCPToolExecutionBase(BaseModel):
    """Base schema for MCP Tool Execution"""
    tool_id: UUID
    input_data: Dict[str, Any]


class MCPToolExecutionCreate(MCPToolExecutionBase):
    """Schema for creating an MCP Tool Execution"""
    session_id: UUID


class MCPToolExecutionUpdate(BaseModel):
    """Schema for updating an MCP Tool Execution"""
    status: Optional[MCPToolExecutionStatus] = None
    output_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None


class MCPToolExecutionPublic(MCPToolExecutionBase):
    """Public schema for MCP Tool Execution"""
    id: UUID
    session_id: UUID
    user_id: UUID
    status: MCPToolExecutionStatus
    output_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MCPToolExecutionsPublic(BaseModel):
    """Schema for list of MCP Tool Executions"""
    data: List[MCPToolExecutionPublic]
    count: int


# WebSocket Message Schemas
class MCPWebSocketMessage(BaseModel):
    """Schema for WebSocket messages in MCP protocol"""
    type: str  # e.g., "request", "response", "notification"
    id: Optional[str] = None
    method: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None


class MCPServerHealthCheck(BaseModel):
    """Schema for MCP Server health check response"""
    server_id: UUID
    status: MCPServerStatus
    last_check: datetime
    response_time_ms: Optional[int] = None
    error: Optional[str] = None
    available_tools: Optional[List[str]] = None