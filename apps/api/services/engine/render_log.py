"""Bounding and redaction for render logs returned to clients.

A CadQuery render's stdout/stderr is handed back to the requester as the render
``log`` and in error events. A cartridge controls what it prints, so the log is
untrusted output on its way to a user: it must be bounded in size (a cartridge
should not be able to stream megabytes back through the event channel) and scrubbed
of anything shaped like a credential or an environment dump, in case a cartridge or
a traceback surfaces one.

The full, unredacted log still goes to the server's own logs (the engine logs it
with ``logger``); only the copy that leaves the server is bounded and redacted.
"""

from __future__ import annotations

import re

# Cap on the log text returned to a client. Generous for genuine render output
# (the longest legitimate commons renders print a few KB) and small enough that a
# cartridge cannot flood the channel.
MAX_RENDER_LOG_CHARS = 16 * 1024

_REDACTED = "[redacted]"

def _redact_kv(m: re.Match[str]) -> str:
    # Keep the identifying name (and its optional quote + separator), redact only
    # the value, so "AWS_SECRET_ACCESS_KEY=[redacted]" stays diagnosable.
    return f"{m.group('name')}{m.group('sep')}{m.group('q')}{_REDACTED}{m.group('q')}"


# Each pattern is applied in order. Bearer first, then key=value, so a
# "Authorization: Bearer <tok>" line is handled by the bearer rule and the
# generic AUTH-name rule does not also fire on it.
_PATTERNS: tuple[tuple[re.Pattern[str], object], ...] = (
    # Bearer tokens.
    (re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._\-]+"), f"Bearer {_REDACTED}"),
    # KEY=value / "KEY": "value" for names that look sensitive. The key may be
    # bare or quoted; the value may be bare or quoted. Only the value is redacted.
    #
    # Every quantifier is bounded and the name must start at a word boundary:
    # the log is untrusted output, and an unbounded ``[A-Z0-9_]*…[A-Z0-9_]*``
    # backtracks polynomially on one long run of word characters, which would let
    # a cartridge stall the process scrubbing its log.
    (re.compile(
        r"(?i)(?<![A-Za-z0-9_])(?P<q0>[\"']?)(?P<name>[A-Z0-9_]{0,48}"
        r"(?:SECRET|TOKEN|PASSWORD|PASSWD|API[_-]?KEY|ACCESS[_-]?KEY|"
        r"CREDENTIAL|PRIVATE[_-]?KEY|SESSION|AUTH)[A-Z0-9_]{0,48})(?P=q0)"
        r"(?P<sep>[ \t]{0,4}[=:][ \t]{0,4})(?P<q>[\"']?)[^\s\"',}]{1,512}(?P=q)"
    ), _redact_kv),
    # AWS access key ids (AKIA/ASIA + 16 base32) are themselves identifying.
    (re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"), _REDACTED),
    # Long AWS-style secret access keys (40-char base64-ish) standing alone.
    (re.compile(r"(?<![A-Za-z0-9/+])[A-Za-z0-9/+]{40}(?![A-Za-z0-9/+])"), _REDACTED),
)

_ENV_DUMP_OPEN = "environ({"
_ENV_DUMP_CLOSE = "})"


def _redact_env_dumps(text: str) -> str:
    """Replace each ``environ({...})`` dump wholesale, in one linear pass.

    Done with ``str.find`` rather than a regex: a lazy ``.*?`` scan restarted at
    every opener is quadratic on many unterminated openers. An opener with no
    closing ``})`` redacts the rest of the text (it is already length-bounded).
    """
    out: list[str] = []
    pos = 0
    while True:
        start = text.find(_ENV_DUMP_OPEN, pos)
        if start < 0:
            out.append(text[pos:])
            break
        out.append(text[pos:start])
        out.append(f"environ({{{_REDACTED}}})")
        end = text.find(_ENV_DUMP_CLOSE, start + len(_ENV_DUMP_OPEN))
        if end < 0:
            break
        pos = end + len(_ENV_DUMP_CLOSE)
    return "".join(out)


def _apply(pattern: re.Pattern[str], repl, text: str) -> str:
    return pattern.sub(repl, text)


def scrub_render_log(text: str) -> str:
    """Redact credential-shaped content from render log *text*.

    Keeps the text otherwise intact so genuine geometry/kernel messages are still
    readable. Never raises; returns ``""`` for a falsy input.
    """
    if not text:
        return ""
    text = _redact_env_dumps(text)
    for pattern, repl in _PATTERNS:
        text = _apply(pattern, repl, text)
    return text


def sanitize_render_log(text: str) -> str:
    """Bound and scrub a render log for return to a client.

    Truncates to ``MAX_RENDER_LOG_CHARS`` (keeping the tail, where the error
    usually is), then redacts credential-shaped content. The result is safe to
    put in a render ``log`` field or an error event.
    """
    if not text:
        return ""
    if len(text) > MAX_RENDER_LOG_CHARS:
        kept = text[-MAX_RENDER_LOG_CHARS:]
        text = f"[log truncated to last {MAX_RENDER_LOG_CHARS} chars]\n{kept}"
    return scrub_render_log(text)
