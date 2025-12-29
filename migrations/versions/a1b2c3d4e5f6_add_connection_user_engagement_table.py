"""Add connection_user_engagement table for per-user tracking

Revision ID: a1b2c3d4e5f6
Revises: 985c025b7396
Create Date: 2025-12-27 02:52:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '985c025b7396'
branch_labels = None
depends_on = None


def upgrade():
    # Create connection_user_engagement table
    op.create_table('connection_user_engagement',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('connection_id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('rating', sa.Enum('up', 'down', name='rating_enum'), nullable=True),
    sa.Column('usage_count', sa.Integer(), nullable=False, server_default='0'),
    sa.Column('first_used_at', sa.DateTime(), nullable=True),
    sa.Column('last_used_at', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['connection_id'], ['connections.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'connection_id', name='unique_user_connection')
    )

    # Create indexes
    op.create_index('ix_connection_user_engagement_connection_id', 'connection_user_engagement', ['connection_id'], unique=False)
    op.create_index('ix_connection_user_engagement_user_id', 'connection_user_engagement', ['user_id'], unique=False)
    op.create_index('ix_connection_user_engagement_usage_count', 'connection_user_engagement', ['usage_count'], unique=False)
    op.create_index('ix_connection_user_engagement_last_used_at', 'connection_user_engagement', ['last_used_at'], unique=False)


def downgrade():
    # Drop indexes
    op.drop_index('ix_connection_user_engagement_last_used_at', table_name='connection_user_engagement')
    op.drop_index('ix_connection_user_engagement_usage_count', table_name='connection_user_engagement')
    op.drop_index('ix_connection_user_engagement_user_id', table_name='connection_user_engagement')
    op.drop_index('ix_connection_user_engagement_connection_id', table_name='connection_user_engagement')

    # Drop table
    op.drop_table('connection_user_engagement')
