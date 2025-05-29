"""Add archived field to mcp_sessions

Revision ID: 311500dbd6ee
Revises: 42dced25f0fd
Create Date: 2025-05-29 15:55:30.119817+00:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '311500dbd6ee'
down_revision = '42dced25f0fd'
branch_labels = None
depends_on = None


def upgrade():
    # Add archived field to mcp_sessions
    op.add_column('mcp_sessions', 
        sa.Column('archived', sa.Boolean(), nullable=False, server_default='false')
    )
    
    # Add archived_at timestamp
    op.add_column('mcp_sessions',
        sa.Column('archived_at', sa.TIMESTAMP(timezone=True), nullable=True)
    )
    
    # Add index for archived sessions
    op.create_index('idx_mcp_sessions_archived', 'mcp_sessions', ['archived', 'user_id'])


def downgrade():
    # Remove index
    op.drop_index('idx_mcp_sessions_archived', table_name='mcp_sessions')
    
    # Remove columns
    op.drop_column('mcp_sessions', 'archived_at')
    op.drop_column('mcp_sessions', 'archived')