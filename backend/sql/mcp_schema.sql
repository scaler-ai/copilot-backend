-- MCP (Model Context Protocol) Database Schema
-- Schema-first approach following existing database patterns

-- ============================================================================
-- ENUMS
-- ============================================================================

-- MCP server connection types
CREATE TYPE mcp_server_type AS ENUM (
    'stdio',     -- Standard input/output based connection
    'http',      -- HTTP-based connection  
    'websocket'  -- WebSocket-based connection
);

-- MCP server operational status
CREATE TYPE mcp_server_status AS ENUM (
    'active',      -- Server is running and available
    'inactive',    -- Server is stopped/disabled
    'error',       -- Server has encountered an error
    'maintenance'  -- Server is under maintenance
);

-- MCP session lifecycle status
CREATE TYPE mcp_session_status AS ENUM (
    'active',    -- Session is ongoing
    'completed', -- Session completed successfully
    'error',     -- Session terminated due to error
    'timeout'    -- Session timed out
);

-- Message roles in MCP conversations
CREATE TYPE mcp_message_role AS ENUM (
    'user',      -- Message from user
    'assistant', -- Message from AI assistant
    'system',    -- System/control message
    'tool'       -- Tool execution result
);

-- Tool execution status tracking
CREATE TYPE mcp_tool_execution_status AS ENUM (
    'pending',  -- Queued for execution
    'running',  -- Currently executing
    'success',  -- Completed successfully
    'failed',   -- Failed to execute
    'timeout'   -- Execution timed out
);

-- ============================================================================
-- TABLES
-- ============================================================================

-- MCP Servers - Configuration for external MCP servers
CREATE TABLE mcp_servers (
    -- Primary key and audit fields (following existing pattern)
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Basic server information
    name VARCHAR(255) NOT NULL,
    description TEXT,
    server_type mcp_server_type NOT NULL,
    status mcp_server_status NOT NULL DEFAULT 'inactive',
    
    -- Connection configuration (JSON for flexibility)
    connection_config JSONB NOT NULL DEFAULT '{}',
    
    -- Enterprise access control (following existing user model pattern)
    owner_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    is_public BOOLEAN NOT NULL DEFAULT FALSE,
    allowed_users JSONB NOT NULL DEFAULT '[]',  -- Array of user UUIDs
    allowed_roles JSONB NOT NULL DEFAULT '[]',  -- Array of role strings
    
    -- Server metadata
    version VARCHAR(50),
    capabilities JSONB NOT NULL DEFAULT '{}',
    last_health_check TIMESTAMPTZ,
    
    -- Indexes for performance
    CONSTRAINT mcp_servers_name_owner_unique UNIQUE (name, owner_id)
);

-- MCP Tools - Tools exposed by MCP servers
CREATE TABLE mcp_tools (
    -- Primary key and audit fields
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Tool identification
    server_id UUID NOT NULL REFERENCES mcp_servers(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- Tool schema (JSON Schema for input validation)
    input_schema JSONB NOT NULL DEFAULT '{}',
    
    -- Tool categorization
    category VARCHAR(100),
    tags JSONB NOT NULL DEFAULT '[]',
    
    -- Usage analytics
    usage_count INTEGER NOT NULL DEFAULT 0,
    last_used TIMESTAMPTZ,
    
    -- Constraints
    CONSTRAINT mcp_tools_name_server_unique UNIQUE (name, server_id)
);

-- MCP Sessions - Conversation sessions with MCP servers
CREATE TABLE mcp_sessions (
    -- Primary key and audit fields
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Session identification
    server_id UUID NOT NULL REFERENCES mcp_servers(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Session metadata
    title VARCHAR(255),
    status mcp_session_status NOT NULL DEFAULT 'active',
    
    -- Session context and metadata
    context JSONB NOT NULL DEFAULT '{}',
    metadata JSONB NOT NULL DEFAULT '{}',
    
    -- Session timing
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    last_activity TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- MCP Messages - Individual messages within sessions
CREATE TABLE mcp_messages (
    -- Primary key and audit fields
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Message identification
    session_id UUID NOT NULL REFERENCES mcp_sessions(id) ON DELETE CASCADE,
    role mcp_message_role NOT NULL,
    content TEXT NOT NULL,
    
    -- Tool-specific fields
    tool_call_id VARCHAR(255),
    tool_name VARCHAR(255),
    
    -- Message metadata
    metadata JSONB NOT NULL DEFAULT '{}'
);

-- MCP Tool Executions - Audit trail for tool usage
CREATE TABLE mcp_tool_executions (
    -- Primary key and audit fields
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Execution identification
    session_id UUID NOT NULL REFERENCES mcp_sessions(id) ON DELETE CASCADE,
    tool_id UUID NOT NULL REFERENCES mcp_tools(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Execution status and data
    status mcp_tool_execution_status NOT NULL DEFAULT 'pending',
    input_data JSONB NOT NULL,
    output_data JSONB,
    error_message TEXT,
    
    -- Execution timing
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    duration_ms INTEGER
);

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================

-- MCP Servers indexes
CREATE INDEX idx_mcp_servers_owner_id ON mcp_servers(owner_id);
CREATE INDEX idx_mcp_servers_status ON mcp_servers(status);
CREATE INDEX idx_mcp_servers_server_type ON mcp_servers(server_type);
CREATE INDEX idx_mcp_servers_is_public ON mcp_servers(is_public);

-- MCP Tools indexes
CREATE INDEX idx_mcp_tools_server_id ON mcp_tools(server_id);
CREATE INDEX idx_mcp_tools_name ON mcp_tools(name);
CREATE INDEX idx_mcp_tools_category ON mcp_tools(category);

-- MCP Sessions indexes
CREATE INDEX idx_mcp_sessions_server_id ON mcp_sessions(server_id);
CREATE INDEX idx_mcp_sessions_user_id ON mcp_sessions(user_id);
CREATE INDEX idx_mcp_sessions_status ON mcp_sessions(status);
CREATE INDEX idx_mcp_sessions_last_activity ON mcp_sessions(last_activity);

-- MCP Messages indexes
CREATE INDEX idx_mcp_messages_session_id ON mcp_messages(session_id);
CREATE INDEX idx_mcp_messages_role ON mcp_messages(role);
CREATE INDEX idx_mcp_messages_created_at ON mcp_messages(created_at);

-- MCP Tool Executions indexes
CREATE INDEX idx_mcp_tool_executions_session_id ON mcp_tool_executions(session_id);
CREATE INDEX idx_mcp_tool_executions_tool_id ON mcp_tool_executions(tool_id);
CREATE INDEX idx_mcp_tool_executions_user_id ON mcp_tool_executions(user_id);
CREATE INDEX idx_mcp_tool_executions_status ON mcp_tool_executions(status);
CREATE INDEX idx_mcp_tool_executions_created_at ON mcp_tool_executions(created_at);

-- ============================================================================
-- TRIGGERS FOR AUTOMATIC UPDATES
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply updated_at triggers to all MCP tables
CREATE TRIGGER update_mcp_servers_updated_at 
    BEFORE UPDATE ON mcp_servers 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_mcp_tools_updated_at 
    BEFORE UPDATE ON mcp_tools 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_mcp_sessions_updated_at 
    BEFORE UPDATE ON mcp_sessions 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_mcp_messages_updated_at 
    BEFORE UPDATE ON mcp_messages 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_mcp_tool_executions_updated_at 
    BEFORE UPDATE ON mcp_tool_executions 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- COMMENTS FOR DOCUMENTATION
-- ============================================================================

-- Table comments
COMMENT ON TABLE mcp_servers IS 'Configuration and metadata for MCP (Model Context Protocol) servers';
COMMENT ON TABLE mcp_tools IS 'Tools exposed by MCP servers with their schemas and usage tracking';
COMMENT ON TABLE mcp_sessions IS 'Conversation sessions between users and MCP servers';
COMMENT ON TABLE mcp_messages IS 'Individual messages within MCP sessions';
COMMENT ON TABLE mcp_tool_executions IS 'Audit trail and tracking for MCP tool executions';

-- Key column comments
COMMENT ON COLUMN mcp_servers.connection_config IS 'JSON configuration for connecting to the MCP server (command, args, url, headers, etc.)';
COMMENT ON COLUMN mcp_servers.capabilities IS 'JSON object describing server capabilities (tools, resources, prompts, etc.)';
COMMENT ON COLUMN mcp_tools.input_schema IS 'JSON Schema defining the expected input format for this tool';
COMMENT ON COLUMN mcp_sessions.context IS 'JSON object storing session-specific context and state';
COMMENT ON COLUMN mcp_tool_executions.input_data IS 'JSON object containing the input parameters for tool execution';
COMMENT ON COLUMN mcp_tool_executions.output_data IS 'JSON object containing the tool execution results';