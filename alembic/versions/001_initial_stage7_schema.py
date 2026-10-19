"""Initial Stage 7 Production Schema

Revision ID: 001_stage7_schema
Revises: 
Create Date: 2026-10-19 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001_stage7_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Users Table
    op.create_table(
        'users',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('username', sa.String(length=100), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_index('ix_users_username', 'users', ['username'], unique=True)

    # 2. Research Sessions Table
    op.create_table(
        'research_sessions',
        sa.Column('id', sa.String(length=128), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('original_query', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='IDLE'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_research_sessions_user_id', 'research_sessions', ['user_id'])
    op.create_index('ix_research_sessions_status', 'research_sessions', ['status'])
    op.create_index('ix_research_sessions_created_at', 'research_sessions', ['created_at'])

    # 3. Research Runs Table
    op.create_table(
        'research_runs',
        sa.Column('id', sa.String(length=128), nullable=False),
        sa.Column('session_id', sa.String(length=128), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('iteration_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='RUNNING'),
        sa.Column('grounding_status', sa.String(length=50), nullable=False, server_default='UNGROUNDED'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['research_sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_research_runs_session_id', 'research_runs', ['session_id'])
    op.create_index('ix_research_runs_user_id', 'research_runs', ['user_id'])
    op.create_index('ix_research_runs_status', 'research_runs', ['status'])

    # 4. Research Iterations Table
    op.create_table(
        'research_iterations',
        sa.Column('id', sa.String(length=128), nullable=False),
        sa.Column('run_id', sa.String(length=128), nullable=False),
        sa.Column('iteration_number', sa.Integer(), nullable=False),
        sa.Column('query_used', sa.Text(), nullable=False),
        sa.Column('papers_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('evidence_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('sufficiency_status', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['run_id'], ['research_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_research_iterations_run_id', 'research_iterations', ['run_id'])

    # 5. Research Jobs Table
    op.create_table(
        'research_jobs',
        sa.Column('id', sa.String(length=128), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('session_id', sa.String(length=128), nullable=False),
        sa.Column('run_id', sa.String(length=128), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='QUEUED'),
        sa.Column('idempotency_key', sa.String(length=128), nullable=True),
        sa.Column('current_step', sa.String(length=100), nullable=True),
        sa.Column('progress_percent', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_code', sa.String(length=50), nullable=True),
        sa.Column('duration_seconds', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['research_sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['run_id'], ['research_runs.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_research_jobs_user_id', 'research_jobs', ['user_id'])
    op.create_index('ix_research_jobs_session_id', 'research_jobs', ['session_id'])
    op.create_index('ix_research_jobs_status', 'research_jobs', ['status'])
    op.create_index('ix_research_jobs_idempotency_key', 'research_jobs', ['idempotency_key'])
    op.create_index('ix_research_jobs_created_at', 'research_jobs', ['created_at'])

    # 6. Reports Table
    op.create_table(
        'reports',
        sa.Column('id', sa.String(length=128), nullable=False),
        sa.Column('session_id', sa.String(length=128), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('run_id', sa.String(length=128), nullable=True),
        sa.Column('markdown_content', sa.Text(), nullable=False),
        sa.Column('evidence_strength', sa.String(length=50), nullable=True),
        sa.Column('claims_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('citations_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('result_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['research_sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['run_id'], ['research_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_reports_session_id', 'reports', ['session_id'])
    op.create_index('ix_reports_user_id', 'reports', ['user_id'])


def downgrade() -> None:
    op.drop_table('reports')
    op.drop_table('research_jobs')
    op.drop_table('research_iterations')
    op.drop_table('research_runs')
    op.drop_table('research_sessions')
    op.drop_table('users')
