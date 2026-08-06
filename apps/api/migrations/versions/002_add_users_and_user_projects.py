"""Add users and user_projects tables.

Revision ID: 002
Revises: 001
Create Date: 2026-04-14

Persistent user storage: stores Janua JWT subjects with tier, preferences,
and project associations.
"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = inspector.get_table_names()

    if "users" not in existing:
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("janua_sub", sa.String(255), nullable=False),
            sa.Column("email", sa.String(320), nullable=True),
            sa.Column("display_name", sa.String(255), nullable=True),
            sa.Column("tier", sa.String(50), nullable=False, server_default="guest"),
            sa.Column("preferences", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                       server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False,
                       server_default=sa.text("CURRENT_TIMESTAMP")),
        )
        op.create_index("ix_users_janua_sub", "users", ["janua_sub"], unique=True)

    if "user_projects" not in existing:
        op.create_table(
            "user_projects",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("project_slug", sa.String(100), nullable=False),
            sa.Column("role", sa.String(50), nullable=False, server_default="editor"),
            sa.Column("last_accessed_at", sa.DateTime(timezone=True), nullable=True,
                       server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.UniqueConstraint("user_id", "project_slug", name="uq_user_project"),
        )
        op.create_index("ix_user_projects_user_id", "user_projects", ["user_id"])
        op.create_index("ix_user_projects_project_slug", "user_projects", ["project_slug"])


def downgrade():
    op.drop_table("user_projects")
    op.drop_table("users")
