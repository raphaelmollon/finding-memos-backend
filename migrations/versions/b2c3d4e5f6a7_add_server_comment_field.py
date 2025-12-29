"""Add server_comment field to connections

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2025-12-29 13:36:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b2c3d4e5f6a7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    # Add url_server_comment column to connections table
    op.add_column('connections', sa.Column('url_server_comment', sa.Text(), nullable=True))


def downgrade():
    # Remove url_server_comment column from connections table
    op.drop_column('connections', 'url_server_comment')
