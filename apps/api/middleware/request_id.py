"""Request ID middleware — attaches a unique ID to every request for tracing."""
import uuid

from flask import g, request


def init_request_id(app):
    """Register before/after request hooks for request ID propagation."""

    @app.before_request
    def _set_request_id():
        g.request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

    @app.after_request
    def _add_request_id_header(response):
        response.headers["X-Request-ID"] = getattr(g, "request_id", "")
        return response
