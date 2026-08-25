"""Add cotiza_quote_events ledger and cotiza_quotes projection.

Revision ID: 003
Revises: 002
Create Date: 2026-08-12

The Cotiza webhook previously handled quote.completed — which carries
total_amount — with a log line. These tables give it an idempotent,
append-only event ledger (deduplicated on a raw-body hash) and a
per-quote projection that revenue reporting can query.
"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = inspector.get_table_names()

    if "cotiza_quote_events" not in existing:
        op.create_table(
            "cotiza_quote_events",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("event_key", sa.String(64), nullable=False),
            sa.Column("event_type", sa.String(50), nullable=False),
            sa.Column("quote_id", sa.String(100), nullable=False),
            sa.Column("quote_number", sa.String(100), nullable=True),
            sa.Column("project_slug", sa.String(100), nullable=True),
            sa.Column("status", sa.String(50), nullable=True),
            sa.Column("total_amount", sa.Numeric(12, 2), nullable=True),
            sa.Column("currency", sa.String(8), nullable=True),
            sa.Column("event_timestamp", sa.String(64), nullable=True),
            sa.Column("received_at", sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("raw", sa.Text(), nullable=True),
        )
        op.create_index(
            "ix_cotiza_quote_events_event_key",
            "cotiza_quote_events", ["event_key"], unique=True,
        )
        op.create_index(
            "idx_cotiza_events_quote_id",
            "cotiza_quote_events", ["quote_id"],
        )

    if "cotiza_quotes" not in existing:
        op.create_table(
            "cotiza_quotes",
            sa.Column("quote_id", sa.String(100), primary_key=True),
            sa.Column("quote_number", sa.String(100), nullable=True),
            sa.Column("project_slug", sa.String(100), nullable=True),
            sa.Column("status", sa.String(50), nullable=True),
            sa.Column("total_amount", sa.Numeric(12, 2), nullable=True),
            sa.Column("currency", sa.String(8), nullable=True),
            sa.Column("last_event_type", sa.String(50), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.text("CURRENT_TIMESTAMP")),
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = inspector.get_table_names()

    if "cotiza_quotes" in existing:
        op.drop_table("cotiza_quotes")
    if "cotiza_quote_events" in existing:
        op.drop_index("ix_cotiza_quote_events_event_key", table_name="cotiza_quote_events")
        op.drop_index("idx_cotiza_events_quote_id", table_name="cotiza_quote_events")
        op.drop_table("cotiza_quote_events")
