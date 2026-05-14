"""Analytics event model — matches the existing SQLite schema for backward compat."""
from extensions import db


class AnalyticsEvent(db.Model):
    __tablename__ = "events"
    __table_args__ = (
        db.Index("idx_events_project", "project"),
        db.Index("idx_events_type", "event_type"),
    )

    id = db.Column(db.Integer, primary_key=True)
    project = db.Column(db.String(100), nullable=False)
    event_type = db.Column(db.String(50), nullable=False)
    event_data = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.Float, nullable=False)

    def __repr__(self):
        return f"<AnalyticsEvent {self.event_type} project={self.project}>"
