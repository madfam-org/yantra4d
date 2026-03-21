"""Initial analytics events table.

Revision ID: 001
Revises: None
Create Date: 2026-03-20

Matches the existing SQLite schema for backward compatibility.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "events" not in inspector.get_table_names():
        op.create_table(
            "events",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("project", sa.String(100), nullable=False),
            sa.Column("event_type", sa.String(50), nullable=False),
            sa.Column("event_data", sa.Text(), nullable=True),
            sa.Column("created_at", sa.Float(), nullable=False),
        )
        op.create_index("idx_events_project", "events", ["project"])
        op.create_index("idx_events_type", "events", ["event_type"])


def downgrade():
    op.drop_index("idx_events_type")
    op.drop_index("idx_events_project")
    op.drop_table("events")
