"""Tests for user_service — upsert, touch_project, and query functions."""
import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_claims(sub="janua|user-1", email="alice@example.com", name="Alice", tier="pro"):
    """Build a minimal JWT claims dict."""
    return {"sub": sub, "email": email, "name": name, "yantra4d_tier": tier}


# ---------------------------------------------------------------------------
# Flask app fixture (in-memory SQLite)
# ---------------------------------------------------------------------------

@pytest.fixture()
def app():
    """Create a minimal Flask app with an in-memory SQLite database."""
    from flask import Flask

    from extensions import db

    test_app = Flask(__name__)
    test_app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    test_app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    test_app.config["TESTING"] = True

    db.init_app(test_app)

    with test_app.app_context():
        # Import models so tables are registered with metadata
        from models.user import User, UserProject  # noqa: F401
        db.create_all()
        yield test_app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def ctx(app):
    """Push an application context for the duration of a test."""
    with app.app_context():
        yield


# ---------------------------------------------------------------------------
# upsert_user_from_claims
# ---------------------------------------------------------------------------

class TestUpsertUserFromClaims:
    """Tests for services.core.user_service.upsert_user_from_claims."""

    def test_creates_new_user_from_claims(self, ctx):
        from models.user import User
        from services.core.user_service import upsert_user_from_claims

        claims = _make_claims()
        user = upsert_user_from_claims(claims)

        assert user is not None
        assert user.janua_sub == "janua|user-1"
        assert user.email == "alice@example.com"
        assert user.display_name == "Alice"
        assert user.tier == "pro"
        assert user.id is not None  # auto-increment assigned

        # Verify persisted to DB
        queried = User.query.filter_by(janua_sub="janua|user-1").first()
        assert queried is not None
        assert queried.id == user.id

    def test_updates_existing_user_on_repeat_upsert(self, ctx):
        from models.user import User
        from services.core.user_service import upsert_user_from_claims

        claims_v1 = _make_claims(email="alice@v1.com", name="Alice V1", tier="essentials")
        user_v1 = upsert_user_from_claims(claims_v1)

        claims_v2 = _make_claims(email="alice@v2.com", name="Alice V2", tier="pro")
        user_v2 = upsert_user_from_claims(claims_v2)

        # Same user record, updated fields
        assert user_v2.id == user_v1.id
        assert user_v2.email == "alice@v2.com"
        assert user_v2.display_name == "Alice V2"
        assert user_v2.tier == "pro"

        # Only one row in DB
        assert User.query.count() == 1

    def test_returns_none_when_claims_missing_sub(self, ctx):
        from services.core.user_service import upsert_user_from_claims

        user = upsert_user_from_claims({"email": "nobody@example.com"})
        assert user is None

    def test_returns_none_on_empty_claims(self, ctx):
        from services.core.user_service import upsert_user_from_claims

        user = upsert_user_from_claims({})
        assert user is None

    def test_handles_none_email_and_name(self, ctx):
        from services.core.user_service import upsert_user_from_claims

        claims = {"sub": "janua|user-no-profile"}
        user = upsert_user_from_claims(claims)

        assert user is not None
        assert user.email is None
        assert user.display_name is None

    def test_sets_last_seen_at_on_each_upsert(self, ctx):
        from services.core.user_service import upsert_user_from_claims

        claims = _make_claims()
        user1 = upsert_user_from_claims(claims)
        first_seen = user1.last_seen_at

        # Upsert again
        user2 = upsert_user_from_claims(claims)
        assert user2.last_seen_at >= first_seen


# ---------------------------------------------------------------------------
# touch_user_project
# ---------------------------------------------------------------------------

class TestTouchUserProject:
    """Tests for services.core.user_service.touch_user_project."""

    def test_creates_new_association(self, ctx):
        from models.user import UserProject
        from services.core.user_service import (
            touch_user_project,
            upsert_user_from_claims,
        )

        user = upsert_user_from_claims(_make_claims())
        assoc = touch_user_project(user, "rugged-box")

        assert assoc is not None
        assert assoc.project_slug == "rugged-box"
        assert assoc.role == "editor"
        assert assoc.user_id == user.id

        # Verify persisted
        assert UserProject.query.count() == 1

    def test_updates_last_accessed_on_repeat_touch(self, ctx):
        from services.core.user_service import (
            touch_user_project,
            upsert_user_from_claims,
        )

        user = upsert_user_from_claims(_make_claims())
        assoc1 = touch_user_project(user, "rugged-box")
        first_access = assoc1.last_accessed_at

        assoc2 = touch_user_project(user, "rugged-box")
        assert assoc2.last_accessed_at >= first_access
        assert assoc2.id == assoc1.id  # same row, not a duplicate

    def test_returns_none_for_none_user(self, ctx):
        from services.core.user_service import touch_user_project

        assert touch_user_project(None, "rugged-box") is None

    def test_returns_none_for_empty_slug(self, ctx):
        from services.core.user_service import (
            touch_user_project,
            upsert_user_from_claims,
        )

        user = upsert_user_from_claims(_make_claims())
        assert touch_user_project(user, "") is None

    def test_supports_custom_role(self, ctx):
        from services.core.user_service import (
            touch_user_project,
            upsert_user_from_claims,
        )

        user = upsert_user_from_claims(_make_claims())
        assoc = touch_user_project(user, "shared-project", role="viewer")

        assert assoc.role == "viewer"


# ---------------------------------------------------------------------------
# get_user_projects
# ---------------------------------------------------------------------------

class TestGetUserProjects:
    """Tests for services.core.user_service.get_user_projects."""

    def test_returns_empty_for_new_user(self, ctx):
        from services.core.user_service import (
            get_user_projects,
            upsert_user_from_claims,
        )

        user = upsert_user_from_claims(_make_claims())
        projects = get_user_projects(user)

        assert projects == []

    def test_returns_projects_sorted_by_last_accessed(self, ctx):
        from services.core.user_service import (
            get_user_projects,
            touch_user_project,
            upsert_user_from_claims,
        )

        user = upsert_user_from_claims(_make_claims())
        touch_user_project(user, "project-a")
        touch_user_project(user, "project-b")
        touch_user_project(user, "project-a")  # re-touch makes it most recent

        projects = get_user_projects(user)

        assert len(projects) == 2
        assert projects[0]["project_slug"] == "project-a"
        assert projects[1]["project_slug"] == "project-b"

    def test_project_dicts_have_expected_keys(self, ctx):
        from services.core.user_service import (
            get_user_projects,
            touch_user_project,
            upsert_user_from_claims,
        )

        user = upsert_user_from_claims(_make_claims())
        touch_user_project(user, "my-project")

        projects = get_user_projects(user)

        assert len(projects) == 1
        p = projects[0]
        assert "project_slug" in p
        assert "role" in p
        assert "last_accessed_at" in p


# ---------------------------------------------------------------------------
# get_user_by_sub
# ---------------------------------------------------------------------------

class TestGetUserBySub:
    """Tests for services.core.user_service.get_user_by_sub."""

    def test_returns_user_when_exists(self, ctx):
        from services.core.user_service import get_user_by_sub, upsert_user_from_claims

        upsert_user_from_claims(_make_claims(sub="janua|lookup-test"))
        user = get_user_by_sub("janua|lookup-test")

        assert user is not None
        assert user.janua_sub == "janua|lookup-test"

    def test_returns_none_when_not_found(self, ctx):
        from services.core.user_service import get_user_by_sub

        assert get_user_by_sub("janua|nonexistent") is None
