"""Add MCP (Model Context Protocol) schema

This migration adds the foundational database schema for MCP server management,
including tables for servers, tools, sessions, messages, and tool executions.

Revision ID: 42dced25f0fd
Revises: 87ddaa4fab90
Create Date: 2025-05-28 12:06:44.054294+00:00

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = '42dced25f0fd'
down_revision = '87ddaa4fab90'
branch_labels = None
depends_on = None


def upgrade():
    # Read and execute the SQL schema file
    import os
    sql_file_path = os.path.join(
        os.path.dirname(__file__), 
        "../../../sql/mcp_schema.sql"
    )
    
    with open(sql_file_path, 'r') as f:
        sql_content = f.read()
    
    # Execute the SQL in smaller chunks to avoid transaction issues
    statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
    
    for statement in statements:
        if statement:
            op.execute(statement)


def downgrade():
    # Drop all MCP tables and types in reverse order
    op.execute("DROP TABLE IF EXISTS mcp_tool_executions CASCADE")
    op.execute("DROP TABLE IF EXISTS mcp_messages CASCADE") 
    op.execute("DROP TABLE IF EXISTS mcp_sessions CASCADE")
    op.execute("DROP TABLE IF EXISTS mcp_tools CASCADE")
    op.execute("DROP TABLE IF EXISTS mcp_servers CASCADE")
    
    # Drop the function
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE")
    
    # Drop the enums
    op.execute("DROP TYPE IF EXISTS mcp_tool_execution_status CASCADE")
    op.execute("DROP TYPE IF EXISTS mcp_message_role CASCADE")
    op.execute("DROP TYPE IF EXISTS mcp_session_status CASCADE")
    op.execute("DROP TYPE IF EXISTS mcp_server_status CASCADE")
    op.execute("DROP TYPE IF EXISTS mcp_server_type CASCADE")
