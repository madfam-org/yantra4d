"""User and UserProject models for persistent user storage."""
from datetime import UTC, datetime

from extensions import db


class User(db.Model):
    """Persistent user record, upserted from Janua JWT claims on each request."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    janua_sub = db.Column(db.String(255), unique=True, nullable=False, index=True)
    email = db.Column(db.String(320), nullable=True)
    display_name = db.Column(db.String(255), nullable=True)
    tier = db.Column(db.String(50), nullable=False, default="guest")
    preferences = db.Column(db.JSON, nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    last_seen_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationship to projects via junction table
    projects = db.relationship(
        "UserProject", back_populates="user", lazy="dynamic",
    )

    def __repr__(self):
        return f"<User {self.janua_sub} tier={self.tier}>"

    def to_dict(self):
        """Serialize user to a JSON-safe dict."""
        return {
            "id": self.id,
            "janua_sub": self.janua_sub,
            "email": self.email,
            "display_name": self.display_name,
            "tier": self.tier,
            "preferences": self.preferences,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_seen_at": self.last_seen_at.isoformat() if self.last_seen_at else None,
        }


class UserProject(db.Model):
    """Junction table linking users to projects with role-based access."""

    __tablename__ = "user_projects"
    __table_args__ = (
        db.UniqueConstraint("user_id", "project_slug", name="uq_user_project"),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    project_slug = db.Column(db.String(100), nullable=False, index=True)
    role = db.Column(db.String(50), nullable=False, default="editor")
    last_accessed_at = db.Column(
        db.DateTime(timezone=True),
        nullable=True,
        default=lambda: datetime.now(UTC),
    )

    # Relationship back to User
    user = db.relationship("User", back_populates="projects")

    def __repr__(self):
        return f"<UserProject user_id={self.user_id} slug={self.project_slug} role={self.role}>"

    def to_dict(self):
        """Serialize to a JSON-safe dict."""
        return {
            "project_slug": self.project_slug,
            "role": self.role,
            "last_accessed_at": self.last_accessed_at.isoformat() if self.last_accessed_at else None,
        }
