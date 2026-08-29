"""Abstract syntax tree for LVL.

The AST is intentionally small and boring. A legal document has a lot of
surface variety, but it reduces to a handful of node kinds: parties, facts,
evidence, claims, rules, deontic obligations, constraints, and queries.
Keeping the node set tiny is what makes the language deterministic to parse
and realistic for a language model to emit.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Union


@dataclass(frozen=True)
class Span:
    """A location in the *source .lvl file* (for error messages)."""

    line: int
    col: int


@dataclass(frozen=True)
class Provenance:
    """A link back to the *legal record* — the whole point of the language.

    A conclusion whose atoms cannot trace to a Provenance is a defect the
    compiler reports. This is the guardrail against a rigorous proof of a
    hallucinated fact.
    """

    doc: Optional[str] = None
    page: Optional[int] = None
    para: Optional[int] = None
    exhibit: Optional[str] = None
    speaker: Optional[str] = None

    def render(self) -> str:
        bits = []
        if self.doc:
            bits.append(self.doc)
        if self.page is not None:
            bits.append(f"p.{self.page}")
        if self.para is not None:
            bits.append(f"¶{self.para}")
        if self.exhibit:
            bits.append(f"[{self.exhibit}]")
        if self.speaker:
            bits.append(f"by {self.speaker}")
        return " ".join(bits) if bits else "(no source)"


# --- Values -----------------------------------------------------------------

@dataclass(frozen=True)
class Money:
    currency: str
    amount: float

    def render(self) -> str:
        return f"{self.currency} {self.amount:,.0f}"


@dataclass(frozen=True)
class DateLit:
    iso: str  # YYYY-MM-DD


@dataclass(frozen=True)
class Ref:
    """A reference to a declared entity or a rule variable."""

    name: str


Value = Union[str, float, Money, DateLit, Ref]


# --- Predicates -------------------------------------------------------------

@dataclass(frozen=True)
class Predicate:
    """``Name(arg, arg, ...)`` — the atoms of legal reasoning."""

    name: str
    args: tuple[str, ...]

    def key(self) -> tuple[str, tuple[str, ...]]:
        return (self.name, self.args)

    def render(self) -> str:
        return f"{self.name}({', '.join(self.args)})"


# --- Top-level declarations -------------------------------------------------

@dataclass
class Jurisdiction:
    name: str
    span: Span


@dataclass
class Party:
    id: str
    type: str          # Person, Org, ...
    label: str         # display name
    span: Span


@dataclass
class Fact:
    id: str
    type: str                       # the typed predicate this fact asserts
    fields: dict[str, Value]
    provenance: Optional[Provenance]
    status_kw: str                  # Established / Alleged / Disputed / ...
    span: Span


@dataclass
class Evidence:
    id: str
    type: str
    fields: dict[str, Value]
    provenance: Optional[Provenance]
    supports: Optional[Predicate]   # proposition this evidence bears on
    refutes: Optional[Predicate]
    span: Span


@dataclass
class Claim:
    id: str
    by: str                         # party id making the claim
    text: str
    asserts: Predicate
    span: Span


@dataclass
class Rule:
    id: str
    head: Predicate
    body: tuple[Predicate, ...]
    connective: str                 # "requires" (AND) | "established_if" (OR) | "normally" (default)
    span: Span
    # For `normally ... except when E ... unless when U ...`: an ordered chain of
    # (kind, predicate) where kind is "except" (rebuts) or "unless" (reinstates).
    # Later clauses have higher priority; the last one that holds decides.
    exceptions: tuple[tuple[str, Predicate], ...] = ()


@dataclass
class Obligation:
    """A deontic node: obligation / permission / prohibition."""

    id: str
    modality: str                   # obligation | permission | prohibition
    bearer: str
    counterparty: Optional[str]
    that: Predicate
    by_date: Optional[DateLit]
    on_breach: Optional[Predicate]
    span: Span


@dataclass
class Constraint:
    """An objective, statically-checkable relation between values.

    ``constraint c1: transfer_17.amount <= cap_amount`` — dates, money and
    durations are things the compiler can *compare* without any legal judgement.
    """

    id: str
    left: Value
    op: str                         # <= >= < > == != | within
    right: Value
    span: Span
    # For the `within N unit direction` duration form:
    n: Optional[int] = None
    unit: Optional[str] = None       # days | weeks | months | years
    direction: Optional[str] = None  # of | before | after


@dataclass
class Exclusive:
    """Declares a set of propositions as mutually exclusive.

    ``exclusive { Loan(t) Investment(t) }`` lets the contradiction checker know
    these cannot both hold, so if both are supported it reports a conflict.
    """

    members: tuple[Predicate, ...]
    span: Span


@dataclass
class Query:
    """An in-file assertion / query. The CLI can also run these ad hoc."""

    kind: str                       # assert | refute | explain | discover
    target: Predicate
    standard: Optional[str]         # for assert/refute
    for_party: Optional[str]
    span: Span


Node = Union[
    Jurisdiction, Party, Fact, Evidence, Claim, Rule,
    Obligation, Constraint, Exclusive, Query,
]


@dataclass
class Program:
    nodes: list[Node] = field(default_factory=list)

    def of_type(self, cls):
        return [n for n in self.nodes if isinstance(n, cls)]
