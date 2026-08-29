"""Tokenizer for LVL.

Newlines and indentation are *insignificant*. The grammar is driven entirely
by keywords, structure (``{}``, ``()``), and predicate shape. This is a
deliberate choice: whitespace-sensitive languages are painful for a language
model to emit reliably, and LVL's whole premise is that an LLM can produce it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Token:
    kind: str      # DATE NUMBER STRING IDENT PUNCT EOF
    value: str
    line: int
    col: int

    def __repr__(self) -> str:  # noqa: DUNDER
        return f"{self.kind}:{self.value!r}@{self.line}:{self.col}"


# Order matters: DATE before NUMBER, longer punctuation before shorter.
_TOKEN_SPEC = [
    ("SKIP",    r"[ \t\r]+"),
    ("NEWLINE", r"\n"),
    ("COMMENT", r"(?:\#|//)[^\n]*"),
    ("DATE",    r"\d{4}-\d{2}-\d{2}"),
    ("NUMBER",  r"\d[\d_]*(?:\.\d+)?"),
    ("STRING",  r'"(?:[^"\\]|\\.)*"'),
    # Dotted identifiers allow jurisdiction/type names like IN.Contract.v1.
    ("IDENT",   r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z0-9_]+)*"),
    ("PUNCT",   r"<=|>=|==|!=|[{}():,=<>]"),
]

_MASTER_RE = re.compile("|".join(f"(?P<{name}>{pat})" for name, pat in _TOKEN_SPEC))


class LexError(SyntaxError):
    pass


def tokenize(src: str) -> list[Token]:
    tokens: list[Token] = []
    line = 1
    line_start = 0
    pos = 0
    n = len(src)
    while pos < n:
        m = _MASTER_RE.match(src, pos)
        if not m:
            col = pos - line_start + 1
            raise LexError(f"unexpected character {src[pos]!r} at line {line}, col {col}")
        kind = m.lastgroup
        text = m.group()
        col = pos - line_start + 1
        if kind == "NEWLINE":
            line += 1
            line_start = m.end()
        elif kind in ("SKIP", "COMMENT"):
            pass
        elif kind == "STRING":
            tokens.append(Token("STRING", _unescape(text[1:-1]), line, col))
        elif kind == "NUMBER":
            tokens.append(Token("NUMBER", text.replace("_", ""), line, col))
        else:
            tokens.append(Token(kind, text, line, col))
        pos = m.end()
    tokens.append(Token("EOF", "", line, 1))
    return tokens


def _unescape(s: str) -> str:
    return s.encode().decode("unicode_escape")
