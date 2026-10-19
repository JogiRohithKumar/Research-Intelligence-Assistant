"""Add Revoked Tokens Table for Multi-Instance JWT Safety

Revision ID: 002_revoked_tokens
Revises: 001_stage7_schema
Create Date: 2026-10-19 19:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002_revoked_tokens'
down_revision: Union[str, None] = '001_stage7_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'revoked_tokens',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=True),
        sa.Column('revoked_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_revoked_tokens_token_hash', 'revoked_tokens', ['token_hash'], unique=True)
    op.create_index('ix_revoked_tokens_user_id', 'revoked_tokens', ['user_id'])


def downgrade() -> None:
    op.drop_table('revoked_tokens')
