"""The formatter must round-trip: format output must re-parse, be idempotent,
and preserve meaning."""

from __future__ import annotations

import pathlib

import pytest

from jvl import Evaluator, compare, parse
from jvl.format import format_program

EXAMPLES = pathlib.Path(__file__).resolve().parents[2] / "examples"
ALL = sorted(p.name for p in EXAMPLES.glob("*.jvl"))


@pytest.mark.parametrize("name", ALL)
def test_format_reparses(name):
    src = (EXAMPLES / name).read_text()
    formatted = format_program(parse(src))
    parse(formatted)  # must not raise


@pytest.mark.parametrize("name", ALL)
def test_format_is_idempotent(name):
    src = (EXAMPLES / name).read_text()
    once = format_program(parse(src))
    twice = format_program(parse(once))
    assert once == twice


@pytest.mark.parametrize("name", ALL)
def test_format_preserves_meaning(name):
    src = (EXAMPLES / name).read_text()
    formatted = format_program(parse(src))
    a = Evaluator(parse(src)).build()
    b = Evaluator(parse(formatted)).build()
    assert compare.equiv(a, b).equivalent
