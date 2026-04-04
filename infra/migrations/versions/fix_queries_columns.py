"""Fix queries table: cost_usd type Integer->Float, add feedback column

Revision ID: fix_queries_columns
Revises: add_api_keys_001
Create Date: 2026-04-04 00:01:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'fix_queries_columns'
down_revision: Union[str, None] = 'add_api_keys_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        'queries',
        'cost_usd',
        existing_type=sa.Integer(),
        type_=sa.Float(),
        existing_nullable=True,
    )
    op.add_column('queries', sa.Column('feedback', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('queries', 'feedback')
    op.alter_column(
        'queries',
        'cost_usd',
        existing_type=sa.Float(),
        type_=sa.Integer(),
        existing_nullable=True,
    )
