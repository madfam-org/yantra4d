"""The source name in a transpiled script's header is written as an escaped literal.

Every other piece of a transpiled script comes from validated values. The source name
(the graph file's base name) is the one piece of free text, and it is written into a
`# Source:` comment. These tests pin how it is written: a plain printable name is
unchanged, so every existing transpilation stays byte-identical, and any line terminator,
control or format character, surrogate, or backslash is written as its Python escape
sequence, so the header comment is always exactly one line.
"""

from __future__ import annotations

import io
import json
import os
import sys
import tokenize

import pytest

from services.engine.graph_engine import prepare_graph_script, transpile

DOC = {
    "version": "1.0.0",
    "units": "mm",
    "nodes": [{"id": "block", "type": "box", "params": {"w": 10, "d": 10, "h": 10}}],
    "outputs": {"block": "block"},
}

# (character, how it must appear in the header). The first seven are the required set:
# the line terminators Python's tokenizer ends a line on (\n, \r, \r\n), the ones
# str.splitlines() adds (form feed, U+2028, U+2029) and NUL. The rest are other control,
# format and surrogate characters, which the same rule covers.
ESCAPED = [
    ("\n", "\\n"),
    ("\r", "\\r"),
    ("\r\n", "\\r\\n"),
    ("\x0c", "\\x0c"),
    ("\x00", "\\x00"),
    ("\u2028", "\\u2028"),
    ("\u2029", "\\u2029"),
    ("\x0b", "\\x0b"),
    ("\x1c", "\\x1c"),
    ("\x1d", "\\x1d"),
    ("\x1e", "\\x1e"),
    ("\x85", "\\x85"),
    ("\t", "\\t"),
    ("\x7f", "\\x7f"),
    ("\u202e", "\\u202e"),
    ("\ufeff", "\\ufeff"),
    ("\ud800", "\\ud800"),
    ("\\", "\\\\"),
]


def _header(script: str) -> str:
    return script.split("\n")[1]


def _reference_lines() -> list[str]:
    return transpile(DOC, {}, source_name="block.graph.json").split("\n")


def test_a_plain_name_is_written_unchanged():
    script = transpile(DOC, {}, source_name="block.graph.json")
    assert _header(script) == "# Source: block.graph.json"


@pytest.mark.parametrize(
    "name",
    ["graph", "x-carriage.graph.json", "pieza ñandú.graph.json", "ab_drive.v2.graph.json"],
)
def test_printable_names_including_spaces_and_non_ascii_are_unchanged(name):
    assert _header(transpile(DOC, {}, source_name=name)) == f"# Source: {name}"


@pytest.mark.parametrize(("char", "escaped"), ESCAPED, ids=[repr(c) for c, _ in ESCAPED])
def test_the_name_is_escaped_and_the_header_stays_one_line(char, escaped):
    name = f"a{char}b.graph.json"
    script = transpile(DOC, {}, source_name=name)
    lines = script.split("\n")
    reference = _reference_lines()

    assert lines[1] == f"# Source: a{escaped}b.graph.json"
    assert lines[1].isprintable()
    # Same shape as a plain name's script: only the header line differs.
    assert len(lines) == len(reference)
    assert lines[:1] + lines[2:] == reference[:1] + reference[2:]
    # No line break of any kind survives anywhere in the script, by every definition.
    assert len(script.splitlines()) == len(reference[:-1])
    assert "\x00" not in script


@pytest.mark.parametrize(("char", "escaped"), ESCAPED, ids=[repr(c) for c, _ in ESCAPED])
def test_the_tokenizer_reads_the_header_as_a_single_comment(char, escaped):
    script = transpile(DOC, {}, source_name=f"a{char}b.graph.json")
    compile(script, "<graph>", "exec")
    tokens = [t for t in tokenize.generate_tokens(io.StringIO(script).readline)]
    comments = [t for t in tokens if t.type == tokenize.COMMENT]
    assert [t.start[0] for t in comments[:2]] == [1, 2]
    assert comments[1].string == f"# Source: a{escaped}b.graph.json"
    # The header comment is followed directly by the end of its line.
    after = tokens[tokens.index(comments[1]) + 1]
    assert after.type == tokenize.NL
    assert after.start[0] == 2


def test_distinct_names_stay_distinct():
    """The escaping is reversible: a literal backslash-n and a line feed differ."""
    real = _header(transpile(DOC, {}, source_name="a\nb.graph.json"))
    literal = _header(transpile(DOC, {}, source_name="a\\nb.graph.json"))
    assert real != literal
    assert literal == "# Source: a\\\\nb.graph.json"


def test_the_engine_bound_source_name_reaches_the_header_escaped(tmp_path):
    """The render-path entrypoint passes the file's base name; it is escaped there too."""
    if sys.platform == "win32":
        pytest.skip("a line feed is not a legal file-name character on Windows")
    graph = tmp_path / "a\nb.graph.json"
    # The script cache keys on content, so make this document's content unique.
    graph.write_text(json.dumps(dict(DOC, meta={"title": str(tmp_path)})), encoding="utf-8")
    script_path = prepare_graph_script(str(graph), None)
    try:
        with open(script_path, encoding="utf-8") as handle:
            script = handle.read()
        assert _header(script) == "# Source: a\\nb.graph.json"
        assert len(script.split("\n")) == len(_reference_lines())
    finally:
        os.unlink(script_path)
