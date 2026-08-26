"""End-to-end tests over the example programs and the epistemic core."""

from __future__ import annotations

import pathlib

import pytest

from jvl import Evaluator, Standard, Status, parse
from jvl.ast import Predicate
from jvl.lattice import combine, join, meet, meets

EXAMPLES = pathlib.Path(__file__).resolve().parents[2] / "examples"


def _eval(name: str) -> Evaluator:
    src = (EXAMPLES / name).read_text()
    return Evaluator(parse(src)).build()


# --- lattice ---------------------------------------------------------------

def test_meet_takes_the_weakest():
    assert meet(Status.PROVEN, Status.SUPPORTED) is Status.SUPPORTED
    assert meet(Status.SUPPORTED, Status.REFUTED) is Status.REFUTED


def test_join_takes_the_strongest():
    assert join(Status.UNKNOWN, Status.SUPPORTED) is Status.SUPPORTED


def test_combine_flags_contradiction_as_disputed():
    assert combine([Status.SUPPORTED, Status.REFUTED]) is Status.DISPUTED


def test_disputed_never_meets_a_standard():
    assert not meets(Status.DISPUTED, Standard.BalanceOfProbabilities)


def test_standard_thresholds():
    assert meets(Status.SUPPORTED, Standard.BalanceOfProbabilities)
    assert not meets(Status.SUPPORTED, Standard.BeyondReasonableDoubt)
    assert meets(Status.PROVEN, Standard.BeyondReasonableDoubt)


# --- example 01: loan vs investment ---------------------------------------

def test_loan_is_supported():
    ev = _eval("01-loan-vs-investment.jvl")
    st = ev.atom_status(Predicate("Loan", ("transfer_17",)).key())
    assert st is Status.SUPPORTED


def test_transfer_is_established_from_a_primary_fact():
    ev = _eval("01-loan-vs-investment.jvl")
    st = ev.atom_status(Predicate("TransferOfValue", ("transfer_17",)).key())
    assert st is Status.ESTABLISHED


def test_removing_the_whatsapp_evidence_collapses_the_loan():
    # The counterfactual the CLI exposes as `jvl simulate --without w17`.
    prog = parse((EXAMPLES / "01-loan-vs-investment.jvl").read_text())
    prog.nodes = [n for n in prog.nodes if getattr(n, "id", None) != "w17"]
    ev = Evaluator(prog).build()
    st = ev.atom_status(Predicate("Loan", ("transfer_17",)).key())
    assert st is Status.UNKNOWN


# --- example 03: criminal offence -----------------------------------------

def test_offence_fails_beyond_reasonable_doubt():
    ev = _eval("03-cheating-s420.jvl")
    verdict = ev.run_assert(Predicate("Cheating", ("payment",)), Standard.BeyondReasonableDoubt)
    assert not verdict.passes


def test_discover_finds_the_missing_mental_element():
    ev = _eval("03-cheating-s420.jvl")
    missing = ev.discover(Predicate("Cheating", ("payment",)))
    names = {p.name for p, _ in missing}
    assert "DishonestIntentionAtInception" in names


def test_contradiction_detected_from_conflicting_evidence():
    ev = _eval("03-cheating-s420.jvl")
    issues = ev.contradictions()
    assert any("PresentAtMeeting" in i for i in issues)


# --- example 02: constraints ----------------------------------------------

def test_default_logic_exception_rebuts_the_conclusion():
    # `normally TimeBarred ... except when Acknowledged` — with the
    # acknowledgement present, the default is rebutted (REFUTED).
    ev = _eval("05-limitation-default.jvl")
    st = ev.atom_status(Predicate("TimeBarred", ("claim1",)).key())
    assert st is Status.REFUTED


def test_removing_the_exception_restores_the_default():
    prog = parse((EXAMPLES / "05-limitation-default.jvl").read_text())
    prog.nodes = [n for n in prog.nodes if getattr(n, "id", None) != "ack"]
    ev = Evaluator(prog).build()
    st = ev.atom_status(Predicate("TimeBarred", ("claim1",)).key())
    assert st is Status.SUPPORTED


def test_objective_constraint_catches_overcap_damages():
    ev = _eval("02-nda-contract.jvl")
    results = {c.id: ok for c, ok, _ in ev.check_constraints()}
    assert results["damages_within_cap"] is False
    assert results["disclosure_before_expiry"] is True


# --- static checks ---------------------------------------------------------

def test_duration_constraint_within_days():
    src = (
        'fact a : T { d: 2025-08-31 } from source(doc="X", page=1) status Established\n'
        'fact b : T { d: 2025-10-15 } from source(doc="Y", page=1) status Established\n'
        'constraint ok: b.d within 60 days after a.d\n'
        'constraint bad: b.d within 30 days after a.d\n'
        'constraint of_ok: b.d within 2 months of a.d\n'
    )
    ev = Evaluator(parse(src)).build()
    results = {c.id: ok for c, ok, _ in ev.check_constraints()}
    assert results["ok"] is True
    assert results["bad"] is False
    assert results["of_ok"] is True


def test_missing_provenance_is_a_warning():
    src = 'fact f : Thing { a: 1 }\nassert Thing(f)'
    diags = Evaluator(parse(src)).build().static_check()
    assert any("provenance" in d.message and d.level == "warning" for d in diags)


def test_claim_by_unknown_party_is_an_error():
    src = 'claim c by Ghost : "x" asserts P(a)'
    diags = Evaluator(parse(src)).build().static_check()
    assert any(d.level == "error" and "undeclared party" in d.message for d in diags)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
