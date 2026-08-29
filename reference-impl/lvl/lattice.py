"""The epistemic lattice — LVL's model of legal truth.

In LVL a proposition is never merely ``true`` or ``false``. It carries an
*epistemic status* drawn from a small lattice, and that status is evaluated
against a *standard of proof*. This module is the single source of truth for
how those statuses combine. Everything else in the evaluator defers to it.

The design goal is honesty: the type system should make it *impossible* to
state a legal conclusion without also stating how well it is supported.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Status(Enum):
    """Epistemic status of a proposition, ordered from worst to best support.

    The ``rank`` (see ``_RANK``) is what ``meet`` (conjunction) and ``join``
    (disjunction) operate on. ``ESTABLISHED`` and ``PROVEN`` share the top rank
    but are distinct members: the former labels a directly asserted primary
    fact, the latter something a rule concluded. They behave identically for
    thresholds but read differently in a derivation trace.

    (They must carry *distinct* enum values — two members with the same value
    would make one a silent alias of the other.)
    """

    REFUTED = "REFUTED"          # evidence shows the proposition is false
    UNSUPPORTED = "UNSUPPORTED"  # asserted or claimed, but nothing backs it
    UNKNOWN = "UNKNOWN"          # no information either way (the default)
    DISPUTED = "DISPUTED"        # evidence points both ways / opposing claims
    SUPPORTED = "SUPPORTED"      # evidence in favour, not conclusive
    PROVEN = "PROVEN"            # established to the required standard (derived)
    ESTABLISHED = "ESTABLISHED"  # established as a primary fact (asserted)

    @property
    def rank(self) -> int:
        return _RANK[self]

    def __str__(self) -> str:  # noqa: DUNDER
        return self.name


_RANK = {
    Status.REFUTED: 0,
    Status.UNSUPPORTED: 1,
    Status.UNKNOWN: 2,
    Status.DISPUTED: 3,
    Status.SUPPORTED: 4,
    Status.PROVEN: 5,
    Status.ESTABLISHED: 5,
}


# Conventional labels: when two statuses tie on rank, which one wins as a
# *derived* result. A rule that concludes something at the top rank reports
# PROVEN, never ESTABLISHED (ESTABLISHED is reserved for primary facts).
_DERIVED_TIE_BREAK = {5: Status.PROVEN}


def meet(a: Status, b: Status) -> Status:
    """Conjunction: an argument is only as strong as its weakest element.

    ``Loan requires TransferOfValue and RepaymentObligation`` — if either
    element is merely SUPPORTED, the conjunction is at best SUPPORTED; if one
    is REFUTED, the whole thing collapses.
    """
    lo = a if a.rank <= b.rank else b
    return _canonical(lo.rank, derived=True)


def join(a: Status, b: Status) -> Status:
    """Disjunction: an ``established_if X or Y`` head takes the stronger branch."""
    hi = a if a.rank >= b.rank else b
    return _canonical(hi.rank, derived=True)


def _canonical(rank: int, derived: bool) -> Status:
    if derived and rank in _DERIVED_TIE_BREAK:
        return _DERIVED_TIE_BREAK[rank]
    # First enum member with this rank.
    for s in Status:
        if s.rank == rank:
            return s
    raise ValueError(f"no status with rank {rank}")


def combine(statuses: list[Status], *, derived: bool = True) -> Status:
    """Aggregate every contribution made to a *single* proposition.

    This is where contradiction becomes visible. If a proposition has both a
    contribution *for* it (SUPPORTED/PROVEN/ESTABLISHED) and one *against* it
    (REFUTED), the result is DISPUTED — the system surfaces the conflict rather
    than silently picking a side.
    """
    if not statuses:
        return Status.UNKNOWN
    has_for = any(s.rank >= Status.SUPPORTED.rank for s in statuses)
    has_against = any(s is Status.REFUTED for s in statuses)
    if has_for and has_against:
        return Status.DISPUTED
    best = max(statuses, key=lambda s: s.rank)
    if best.rank == 5:
        # A primary, directly-asserted fact reads ESTABLISHED; anything a rule
        # concluded reads PROVEN. Preserve the distinction in the trace.
        if Status.ESTABLISHED in statuses and Status.PROVEN not in statuses:
            return Status.ESTABLISHED
        return Status.PROVEN
    return best


# --- Standards of proof -----------------------------------------------------

class Standard(Enum):
    """How strong the support must be for a proposition to *hold*.

    The mapping to a minimum rank (``threshold``) is deliberately simple and is
    documented as a simplification in docs/04-semantics.md. Real standards of
    proof are not a single scalar; this is a first, checkable approximation.
    """

    BalanceOfProbabilities = "BalanceOfProbabilities"  # "more likely than not"
    ClearAndConvincing = "ClearAndConvincing"          # stricter in doctrine
    BeyondReasonableDoubt = "BeyondReasonableDoubt"     # near-certainty

    @property
    def threshold(self) -> int:
        return _THRESHOLD[self]

    @classmethod
    def parse(cls, name: str) -> "Standard":
        try:
            return cls[name]
        except KeyError as exc:
            valid = ", ".join(s.name for s in cls)
            raise ValueError(f"unknown standard of proof '{name}'. Try one of: {valid}") from exc


_THRESHOLD = {
    Standard.BalanceOfProbabilities: Status.SUPPORTED.rank,   # 4
    Standard.ClearAndConvincing: Status.SUPPORTED.rank,       # 4 (see docs note)
    Standard.BeyondReasonableDoubt: Status.PROVEN.rank,       # 5
}


def meets(status: Status, standard: Standard) -> bool:
    """Does ``status`` clear the bar set by ``standard``?"""
    if status is Status.DISPUTED:
        # A disputed proposition never *meets* a standard on its own — the
        # conflict has to be resolved first.
        return False
    return status.rank >= standard.threshold


# Map the fact-declaration keywords a user writes to lattice statuses.
FACT_STATUS_KEYWORDS = {
    "Established": Status.ESTABLISHED,
    "Admitted": Status.ESTABLISHED,   # conceded by the opposing party
    "Proven": Status.PROVEN,
    "Supported": Status.SUPPORTED,
    "Alleged": Status.UNSUPPORTED,
    "Disputed": Status.DISPUTED,
    "Refuted": Status.REFUTED,
    "Unknown": Status.UNKNOWN,
}


@dataclass(frozen=True)
class Verdict:
    """The outcome of an ``assert`` against a standard of proof."""

    status: Status
    standard: Standard
    passes: bool

    @classmethod
    def of(cls, status: Status, standard: Standard) -> "Verdict":
        return cls(status=status, standard=standard, passes=meets(status, standard))
