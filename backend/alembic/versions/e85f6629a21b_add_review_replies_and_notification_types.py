"""add_review_replies_and_notification_types

Revision ID: e85f6629a21b
Revises: d74c55379104
Create Date: 2026-09-02 09:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e85f6629a21b'
down_revision: Union[str, None] = 'd74c55379104'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add provider reply columns to reviews
    op.add_column('reviews', sa.Column('provider_reply', sa.Text(), nullable=True))
    op.add_column('reviews', sa.Column('replied_at', sa.DateTime(timezone=True), nullable=True))

    # Add new enum values to notification_type_enum in postgres
    op.execute("ALTER TYPE notification_type_enum ADD VALUE IF NOT EXISTS 'NEW_JOB';")
    op.execute("ALTER TYPE notification_type_enum ADD VALUE IF NOT EXISTS 'JOB_CANCELLED';")


def downgrade() -> None:
    op.drop_column('reviews', 'replied_at')
    op.drop_column('reviews', 'provider_reply')
