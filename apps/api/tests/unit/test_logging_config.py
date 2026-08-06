"""Tests for logging configuration."""
import json
import logging
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[2]))

from utils.logging_config import JSONFormatter, setup_logging


class TestLoggingConfig:
    def test_setup_text_mode(self):
        with patch.dict("os.environ", {"LOG_FORMAT": "text"}):
            setup_logging(debug=False)
        root = logging.getLogger()
        assert len(root.handlers) > 0
        assert not isinstance(root.handlers[0].formatter, JSONFormatter)

    def test_setup_json_mode(self):
        with patch.dict("os.environ", {"LOG_FORMAT": "json"}):
            setup_logging(debug=False)
        root = logging.getLogger()
        assert isinstance(root.handlers[0].formatter, JSONFormatter)

    def test_json_formatter_output(self):
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="hello world",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
        parsed = json.loads(output)
        assert parsed["level"] == "INFO"
        assert parsed["message"] == "hello world"
        assert parsed["logger"] == "test"
        assert "timestamp" in parsed

    def test_debug_mode_sets_debug_level(self):
        setup_logging(debug=True)
        root = logging.getLogger()
        assert root.level == logging.DEBUG

    def test_info_mode_sets_info_level(self):
        setup_logging(debug=False)
        root = logging.getLogger()
        assert root.level == logging.INFO

    def test_clears_existing_handlers(self):
        root = logging.getLogger()
        root.addHandler(logging.StreamHandler())
        root.addHandler(logging.StreamHandler())
        assert len(root.handlers) >= 2
        setup_logging(debug=False)
        assert len(root.handlers) == 1

    def test_json_formatter_includes_request_id_in_flask_context(self):
        from app import create_app
        app = create_app()
        formatter = JSONFormatter()

        with app.test_request_context("/"):
            from flask import g
            g.request_id = "test-rid-456"

            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="",
                lineno=0,
                msg="with request context",
                args=(),
                exc_info=None,
            )
            output = formatter.format(record)
            parsed = json.loads(output)
            assert parsed["request_id"] == "test-rid-456"

    def test_json_formatter_omits_request_id_outside_context(self):
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.WARNING,
            pathname="",
            lineno=0,
            msg="no context",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
        parsed = json.loads(output)
        assert "request_id" not in parsed

    def test_json_formatter_includes_duration_ms(self):
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="timed op",
            args=(),
            exc_info=None,
        )
        record.duration_ms = 42.5
        output = formatter.format(record)
        parsed = json.loads(output)
        assert parsed["duration_ms"] == 42.5

    def test_json_formatter_includes_exception(self):
        formatter = JSONFormatter()
        try:
            raise ValueError("test error")
        except ValueError:
            import sys
            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="",
            lineno=0,
            msg="with exc",
            args=(),
            exc_info=exc_info,
        )
        output = formatter.format(record)
        parsed = json.loads(output)
        assert "exception" in parsed
        assert "ValueError" in parsed["exception"]
