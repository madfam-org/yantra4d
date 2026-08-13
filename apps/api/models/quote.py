"""Cotiza quote projection — the queryable order state the webhook feeds.

Two tables with distinct jobs:

- `cotiza_quote_events` is the append-only ledger. One row per *distinct*
  webhook delivery, deduplicated by a hash of the raw body, so a provider
  retry or a replayed request is a no-op instead of a double-counted order.
  The full payload is kept for audit and reprojection.
- `cotiza_quotes` is the projection: one row per quote_id carrying the
  latest known status and amount. This is what revenue reporting reads —
  before this table existed, `quote.completed` amounts arrived and were
  written to a log line only.
"""
from extensions import db


class CotizaQuoteEvent(db.Model):
    __tablename__ = "cotiza_quote_events"
    __table_args__ = (
        db.Index("idx_cotiza_events_quote_id", "quote_id"),
        # Unique as an explicit named index (not column-level unique=True) so
        # the model and migration describe the same DDL and `flask db check`
        # sees no drift.
        db.Index("ix_cotiza_quote_events_event_key", "event_key", unique=True),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    # sha256 hex of the raw request body — the idempotency key. Identical
    # redelivery (provider retry, replay) hits the unique index and is
    # acknowledged without effect.
    event_key = db.Column(db.String(64), nullable=False)
    event_type = db.Column(db.String(50), nullable=False)
    quote_id = db.Column(db.String(100), nullable=False)
    quote_number = db.Column(db.String(100), nullable=True)
    project_slug = db.Column(db.String(100), nullable=True)
    status = db.Column(db.String(50), nullable=True)
    # Numeric, not float: this is money.
    total_amount = db.Column(db.Numeric(12, 2), nullable=True)
    currency = db.Column(db.String(8), nullable=True)
    # Provider timestamp exactly as sent; ordering authority stays with Cotiza.
    event_timestamp = db.Column(db.String(64), nullable=True)
    received_at = db.Column(
        db.DateTime(timezone=True), nullable=False,
        server_default=db.text("CURRENT_TIMESTAMP"),
    )
    raw = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f"<CotizaQuoteEvent {self.event_type} quote={self.quote_id}>"


class CotizaQuote(db.Model):
    __tablename__ = "cotiza_quotes"

    quote_id = db.Column(db.String(100), primary_key=True)
    quote_number = db.Column(db.String(100), nullable=True)
    project_slug = db.Column(db.String(100), nullable=True)
    status = db.Column(db.String(50), nullable=True)
    total_amount = db.Column(db.Numeric(12, 2), nullable=True)
    currency = db.Column(db.String(8), nullable=True)
    last_event_type = db.Column(db.String(50), nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False,
        server_default=db.text("CURRENT_TIMESTAMP"),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False,
        server_default=db.text("CURRENT_TIMESTAMP"),
    )

    def __repr__(self):
        return f"<CotizaQuote {self.quote_id} status={self.status}>"
