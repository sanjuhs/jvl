"""Tests for emit (serialize) and diff/equiv (compare)."""

from __future__ import annotations

import json
import pathlib

from lvl import Evaluator, parse
from lvl import compare, serialize

EXAMPLES = pathlib.Path(__file__).resolve().parents[2] / "examples"


def _eval_src(src: str) -> Evaluator:
    return Evaluator(parse(src)).build()


def _eval_file(name: str) -> Evaluator:
    return Evaluator(parse((EXAMPLES / name).read_text())).build()


# --- serialize -------------------------------------------------------------

def test_emit_json_is_valid_and_has_atoms():
    ev = _eval_file("01-loan-vs-investment.lvl")
    data = json.loads(serialize.to_json(ev))
    assert data["jurisdiction"] == "IN.Contract.v1"
    props = {a["proposition"]: a["status"] for a in data["atoms"]}
    assert props["Loan(transfer_17)"] == "SUPPORTED"
    assert props["TransferOfValue(transfer_17)"] == "ESTABLISHED"


def test_emit_json_is_deterministic():
    ev1 = _eval_file("02-nda-contract.lvl")
    ev2 = _eval_file("02-nda-contract.lvl")
    assert serialize.to_json(ev1) == serialize.to_json(ev2)


def test_emit_graph_has_supports_edge():
    ev = _eval_file("01-loan-vs-investment.lvl")
    g = serialize.to_graph(ev)
    rels = {(e["from"], e["rel"], e["to"]) for e in g["edges"]}
    assert ("w17", "supports", "RepaymentObligation(transfer_17)") in rels


# --- diff / equiv ----------------------------------------------------------

def test_identical_programs_are_equivalent():
    a = _eval_file("04-service-agreement-v1.lvl")
    b = _eval_file("04-service-agreement-v1.lvl")
    assert compare.equiv(a, b).equivalent


def test_reordering_and_comments_do_not_break_equivalence():
    base = (EXAMPLES / "04-service-agreement-v1.lvl").read_text()
    # Reverse the statement order and strip comments — pure cosmetics.
    lines = [ln for ln in base.splitlines() if not ln.strip().startswith("#")]
    a = _eval_src(base)
    b = _eval_src("\n".join(lines))
    assert compare.equiv(a, b).equivalent


def test_amended_contract_is_not_equivalent():
    a = _eval_file("04-service-agreement-v1.lvl")
    b = _eval_file("04-service-agreement-v2.lvl")
    result = compare.equiv(a, b)
    assert not result.equivalent
    # The fee change is an operative-term difference and must be caught.
    assert any("fee" in d for d in result.discriminating)


def test_diff_reports_fact_and_rule_changes():
    a = _eval_file("04-service-agreement-v1.lvl")
    b = _eval_file("04-service-agreement-v2.lvl")
    d = compare.diff(a, b)
    assert "penalty_clause" in d.rules_added
    assert any("fee" in c for c in d.fact_changes)
