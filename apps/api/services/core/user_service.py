"""
User service: upsert user records from JWT claims and manage user-project associations.
"""
import logging
from datetime import datetime, timezone

from extensions import db
from models.user import User, UserProject
from services.core.tier_service import resolve_tier

logger = logging.getLogger(__name__)


def upsert_user_from_claims(claims: dict) -> User | None:
    """Create or update a User record from decoded JWT claims.

    Updates email, display_name, tier, and last_seen_at on every call.
    Returns the User instance, or None if claims lack a 'sub' field.
    """
    sub = claims.get("sub")
    if not sub:
        logger.warning("JWT claims missing 'sub' field, cannot upsert user")
        return None

    email = claims.get("email")
    display_name = claims.get("name")
    tier = resolve_tier(claims)
    now = datetime.now(timezone.utc)

    user = User.query.filter_by(janua_sub=sub).first()

    if user is None:
        user = User(
            janua_sub=sub,
            email=email,
            display_name=display_name,
            tier=tier,
            created_at=now,
            last_seen_at=now,
        )
        db.session.add(user)
        logger.info("Created new user record for sub=%s tier=%s", sub, tier)
    else:
        user.email = email
        user.display_name = display_name
        user.tier = tier
        user.last_seen_at = now

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception("Failed to upsert user for sub=%s", sub)
        return None

    return user


def touch_user_project(user: User, project_slug: str, role: str = "editor") -> UserProject | None:
    """Record or update a user's association with a project.

    Creates the association if it does not exist, otherwise updates last_accessed_at.
    Returns the UserProject instance.
    """
    if not user or not project_slug:
        return None

    now = datetime.now(timezone.utc)

    assoc = UserProject.query.filter_by(
        user_id=user.id, project_slug=project_slug,
    ).first()

    if assoc is None:
        assoc = UserProject(
            user_id=user.id,
            project_slug=project_slug,
            role=role,
            last_accessed_at=now,
        )
        db.session.add(assoc)
        logger.info("Created user-project association: user=%s project=%s role=%s", user.id, project_slug, role)
    else:
        assoc.last_accessed_at = now

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception("Failed to touch user-project for user=%s project=%s", user.id, project_slug)
        return None

    return assoc


def get_user_by_sub(janua_sub: str) -> User | None:
    """Look up a user by their Janua subject identifier."""
    return User.query.filter_by(janua_sub=janua_sub).first()


def get_user_projects(user: User) -> list[dict]:
    """Return all projects associated with a user, ordered by last accessed."""
    assocs = (
        UserProject.query
        .filter_by(user_id=user.id)
        .order_by(UserProject.last_accessed_at.desc())
        .all()
    )
    return [a.to_dict() for a in assocs]
