"""Tests for render-log bounding and credential scrubbing."""
from services.engine.render_log import (
    MAX_RENDER_LOG_CHARS,
    sanitize_render_log,
    scrub_render_log,
)


def test_empty_is_empty():
    assert sanitize_render_log("") == ""
    assert sanitize_render_log(None) == ""  # type: ignore[arg-type]
    assert scrub_render_log(None) == ""  # type: ignore[arg-type]


def test_truncates_to_bound_keeping_tail():
    text = "A" * (MAX_RENDER_LOG_CHARS + 5000) + "TAIL-ERROR"
    out = sanitize_render_log(text)
    assert len(out) <= MAX_RENDER_LOG_CHARS + 100  # bound + the marker line
    assert "TAIL-ERROR" in out
    assert "truncated" in out


def test_redacts_secret_key_value_pairs():
    text = "AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
    out = sanitize_render_log(text)
    assert "wJalrXUtnFEMI" not in out
    # The identifying name is kept so the error stays diagnosable.
    assert "AWS_SECRET_ACCESS_KEY" in out
    assert "[redacted]" in out


def test_redacts_json_style_token():
    text = '{"api_key": "sk-abcdef0123456789abcdef"}'
    out = sanitize_render_log(text)
    assert "sk-abcdef0123456789abcdef" not in out
    assert "[redacted]" in out


def test_redacts_aws_access_key_id():
    text = "using key AKIAIOSFODNN7EXAMPLE for upload"
    out = sanitize_render_log(text)
    assert "AKIAIOSFODNN7EXAMPLE" not in out
    assert "[redacted]" in out


def test_redacts_bearer_token():
    text = "log line: Bearer eyJhbG.ciOiJ.IUzI1NiJ9 end"
    out = sanitize_render_log(text)
    assert "eyJhbG" not in out
    assert "[redacted]" in out


def test_redacts_authorization_bearer_header():
    # Belt and suspenders: both the Authorization name and its Bearer token are
    # redacted; the token value never survives.
    text = "Authorization: Bearer eyJhbG.ciOiJ.IUzI1NiJ9"
    out = sanitize_render_log(text)
    assert "eyJhbG" not in out
    assert "[redacted]" in out


def test_redacts_environ_dump():
    text = "environ({'PATH': '/bin', 'AWS_SECRET_ACCESS_KEY': 'abc'})"
    out = sanitize_render_log(text)
    assert "abc" not in out
    assert "[redacted]" in out


def test_keeps_ordinary_render_output():
    text = "Loading parameters: {}\nExecuting CadQuery script\nRendering complete."
    out = sanitize_render_log(text)
    assert "Rendering complete." in out
    assert "Executing CadQuery script" in out


def test_scrub_is_linear_on_adversarial_input():
    """The log is untrusted cartridge output: no input shape may make the
    scrubber backtrack. Each case is far larger than the client bound and must
    still finish quickly (it ran for minutes with an unbounded pattern)."""
    import time

    cases = [
        "A" * 200_000,                       # one long word-character run
        "SECRET" * 40_000,                   # repeated sensitive-name fragment
        "x_TOKEN_" * 30_000 + "=",            # name-shaped run, separator at the end
        "environ({" * 30_000,                # unterminated env-dump openers
        ("a/" * 25) * 8_000,                 # near-miss secret-key charset
    ]
    for text in cases:
        started = time.monotonic()
        scrub_render_log(text)
        sanitize_render_log(text)
        assert time.monotonic() - started < 2.0, f"slow on {text[:20]!r}…"
