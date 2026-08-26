"""Parser and lexer unit tests."""

from __future__ import annotations

import pytest

from jvl import ast, parse
from jvl.lexer import tokenize
from jvl.parser import ParseError


def test_tokenize_money_and_dates():
    toks = [t.kind for t in tokenize("fact f : T { amount: INR 1_000_000 on: 2025-03-10 }")]
    assert "DATE" in toks and "NUMBER" in toks


def test_comments_are_ignored():
    prog = parse("# a comment\n// another\njurisdiction X.Y.v1")
    assert len(prog.of_type(ast.Jurisdiction)) == 1


def test_parse_fact_with_provenance_and_status():
    prog = parse(
        'fact t : TransferOfValue { amount: INR 1000 } '
        'from source(doc="B", page=2, para=4) status Established'
    )
    fact = prog.of_type(ast.Fact)[0]
    assert fact.type == "TransferOfValue"
    assert fact.provenance.doc == "B" and fact.provenance.para == 4
    assert fact.status_kw == "Established"


def test_parse_rule_conjunction_and_disjunction():
    prog = parse(
        "rule r1: Loan(t) requires TransferOfValue(t) RepaymentObligation(t)\n"
        "rule r2: Repay(t) established_if Admitted(t) or ContractSays(t)"
    )
    r1, r2 = prog.of_type(ast.Rule)
    assert r1.connective == "requires" and len(r1.body) == 2
    assert r2.connective == "established_if" and len(r2.body) == 2


def test_rule_body_terminates_before_next_statement():
    prog = parse(
        "rule r: Head(t) requires A(t) B(t)\n"
        "assert Head(x)"
    )
    assert len(prog.of_type(ast.Rule)[0].body) == 2
    assert len(prog.of_type(ast.Query)) == 1


def test_exclusive_block():
    prog = parse("exclusive { Loan(t) Investment(t) }")
    assert len(prog.of_type(ast.Exclusive)[0].members) == 2


def test_constraint_with_dotted_reference():
    prog = parse("constraint c: a.amount <= b.cap")
    c = prog.of_type(ast.Constraint)[0]
    assert c.op == "<=" and isinstance(c.left, ast.Ref) and c.left.name == "a.amount"


def test_bad_syntax_raises_parse_error():
    with pytest.raises(ParseError):
        parse("party A Person")  # missing '='


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
