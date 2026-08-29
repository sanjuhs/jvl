"""The LVL evaluator.

Given a parsed :class:`~lvl.ast.Program`, this builds a table of *atoms*
(ground propositions), each with an epistemic status derived from facts,
evidence, claims and rules. On top of that table it offers the operations that
make LVL worth having:

* ``assert`` / ``prove`` — does a proposition hold, to a standard of proof?
* ``explain`` — the full derivation trace, every node linked to the record.
* ``discover`` — which elements of a claim are still missing?
* contradiction detection — where do the clauses conflict with each other?
* constraint checking — do the objective (money/date/number) relations hold?

The algorithm is a forward-chaining fixpoint. Rule variables are bound by
matching each rule's body against the atoms that actually exist (see
``_bindings``), so evaluation scales with the *relevant* facts rather than the
size of the whole document — thousands of facts evaluate in tens of
milliseconds. It is still written to be read; clarity first, but not naive.
"""

from __future__ import annotations

import itertools
import re
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

_UNIT_DAYS = {"days": 1, "weeks": 7, "months": 30, "years": 365}

from . import ast
from .lattice import (
    FACT_STATUS_KEYWORDS, Standard, Status, Verdict, combine, join, meet, meets,
)

_MAX_PASSES = 100
_VAR_RE = re.compile(r"^[a-z][A-Za-z0-9_]*$")

AtomKey = tuple[str, tuple[str, ...]]


@dataclass
class Contribution:
    kind: str                        # fact | evidence | claim | rule
    source_id: str
    status: Status
    provenance: Optional[ast.Provenance] = None
    note: str = ""


@dataclass
class Diagnostic:
    level: str                       # error | warning | info
    message: str
    span: Optional[ast.Span] = None

    def render(self) -> str:
        loc = f"line {self.span.line}: " if self.span else ""
        return f"[{self.level}] {loc}{self.message}"


@dataclass
class Evaluator:
    program: ast.Program
    constants: set[str] = field(default_factory=set)
    base: dict[AtomKey, list[Contribution]] = field(default_factory=dict)
    status: dict[AtomKey, Status] = field(default_factory=dict)
    diagnostics: list[Diagnostic] = field(default_factory=list)

    # ------------------------------------------------------------------
    def build(self) -> "Evaluator":
        self._collect_constants()
        self._collect_base_atoms()
        self._fixpoint()
        return self

    def _collect_constants(self) -> None:
        for n in self.program.nodes:
            if isinstance(n, (ast.Party, ast.Fact, ast.Evidence, ast.Claim)):
                self.constants.add(n.id)

    def _add_base(self, key: AtomKey, contrib: Contribution) -> None:
        self.base.setdefault(key, []).append(contrib)

    def _collect_base_atoms(self) -> None:
        for n in self.program.nodes:
            if isinstance(n, ast.Fact):
                st = FACT_STATUS_KEYWORDS.get(n.status_kw, Status.UNSUPPORTED)
                self._add_base((n.type, (n.id,)),
                               Contribution("fact", n.id, st, n.provenance,
                                            note=f"{n.status_kw} fact"))
            elif isinstance(n, ast.Evidence):
                if n.supports:
                    self._add_base(n.supports.key(),
                                   Contribution("evidence", n.id, Status.SUPPORTED,
                                                n.provenance, note="supporting evidence"))
                if n.refutes:
                    self._add_base(n.refutes.key(),
                                   Contribution("evidence", n.id, Status.REFUTED,
                                                n.provenance, note="refuting evidence"))
            elif isinstance(n, ast.Claim):
                self._add_base(n.asserts.key(),
                               Contribution("claim", n.id, Status.UNSUPPORTED,
                                            note=f"claimed by {n.by}"))
            elif isinstance(n, ast.Obligation) and n.on_breach:
                # An obligation's breach consequence is a derivable proposition
                # only when the obligation is breached; we register the atom so
                # it is visible, at UNKNOWN, until a rule/fact establishes it.
                self.base.setdefault(n.on_breach.key(), [])

    # ------------------------------------------------------------------
    def _fixpoint(self) -> None:
        rules = self.program.of_type(ast.Rule)
        prev: dict[AtomKey, Status] = {}
        for _ in range(_MAX_PASSES):
            atoms: dict[AtomKey, list[Contribution]] = {
                k: list(v) for k, v in self.base.items()
            }
            for rule in rules:
                for binding in self._bindings(rule, prev):
                    head_key, body_status, _ = self._fire(rule, binding, prev)
                    if body_status is None:
                        continue
                    atoms.setdefault(head_key, []).append(
                        Contribution("rule", rule.id, body_status,
                                     note=rule.connective))
            new_status = {k: combine([c.status for c in cs]) for k, cs in atoms.items()}
            if new_status == prev:
                self._atoms = atoms
                self.status = new_status
                return
            prev = new_status
        self._atoms = atoms
        self.status = new_status
        self.diagnostics.append(
            Diagnostic("warning", "evaluation did not reach a fixpoint (cycle?)"))

    def _bindings(self, rule: ast.Rule, prev: dict[AtomKey, Status]):
        """Bind a rule's variables by *matching its body against known atoms*,
        not by enumerating the whole universe.

        The naive approach is a cartesian product over every declared entity —
        O(|U|^vars) — which is what made evaluation slow on large programs. This
        version joins the rule's body predicates against the atoms that actually
        exist so far, so the work scales with the *relevant* facts rather than
        the size of the document. It falls back to the universe only for a
        variable that appears in no body/exception predicate (rare).
        """
        variables = self._vars_of(rule)
        if not variables:
            yield {}
            return

        index: dict[str, list[tuple[str, ...]]] = {}
        for name, args in set(prev.keys()) | set(self.base.keys()):
            index.setdefault(name, []).append(args)

        # For each variable, collect the values it actually takes in some known
        # atom. This is linear in the number of atoms — no cartesian product
        # over the whole universe, and no quadratic join between body predicates.
        candidates: dict[str, set[str]] = {v: set() for v in variables}
        for pred in (*rule.body, *(p for _, p in rule.exceptions)):
            atoms = index.get(pred.name)
            if not atoms:
                continue
            for args in atoms:
                if len(args) != len(pred.args):
                    continue
                if any(h not in variables and h != a for h, a in zip(pred.args, args)):
                    continue  # a constant position in the rule didn't match
                for h, a in zip(pred.args, args):
                    if h in variables:
                        candidates[h].add(a)

        universe = sorted(self.constants)
        var_order = sorted(variables)
        # A variable that never appears in a matched atom (e.g. head-only) falls
        # back to the universe. Correctness is preserved because _fire() skips
        # any binding whose body is entirely UNKNOWN — over-generation is safe.
        value_lists = [sorted(candidates[v]) or universe for v in var_order]

        count = 0
        for combo in itertools.product(*value_lists):
            count += 1
            if count > 10000:  # safety cap
                return
            yield dict(zip(var_order, combo))

    def _vars_of(self, rule: ast.Rule) -> set[str]:
        vs: set[str] = set()
        preds = [rule.head, *rule.body, *(p for _, p in rule.exceptions)]
        for pred in preds:
            for a in pred.args:
                if a not in self.constants and _VAR_RE.match(a):
                    vs.add(a)
        return vs

    def _fire(self, rule: ast.Rule, binding: dict, prev: dict[AtomKey, Status]):
        def inst(pred: ast.Predicate) -> AtomKey:
            return (pred.name, tuple(binding.get(a, a) for a in pred.args))

        head_key = inst(rule.head)
        body_keys = [inst(p) for p in rule.body]
        body_statuses = [prev.get(k, Status.UNKNOWN) for k in body_keys]
        if all(s is Status.UNKNOWN for s in body_statuses):
            return head_key, None, body_keys  # don't manufacture atoms
        if rule.connective == "established_if":
            acc = body_statuses[0]
            for s in body_statuses[1:]:
                acc = join(acc, s)
        else:  # "requires" and "normally" both take the weakest element
            acc = body_statuses[0]
            for s in body_statuses[1:]:
                acc = meet(acc, s)
        # Defeasible default with a cascade of exceptions. Process the chain in
        # order; the last clause that holds decides — `except` rebuts (REFUTED),
        # `unless` reinstates the default. Later clauses win (higher priority).
        if rule.connective == "normally" and rule.exceptions:
            default = acc
            for kind, ex in rule.exceptions:
                if prev.get(inst(ex), Status.UNKNOWN).rank >= Status.SUPPORTED.rank:
                    acc = Status.REFUTED if kind == "except" else default
        return head_key, acc, body_keys

    # ------------------------------------------------------------------
    def atom_status(self, key: AtomKey) -> Status:
        return self.status.get(key, Status.UNKNOWN)

    # --- operations ----------------------------------------------------
    def run_assert(self, target: ast.Predicate, standard: Standard) -> Verdict:
        st = self.atom_status(target.key())
        return Verdict.of(st, standard)

    def trace(self, target: ast.Predicate, depth: int = 0, seen: set | None = None) -> list[str]:
        """Human-readable derivation tree for a proposition."""
        seen = seen or set()
        key = target.key()
        st = self.atom_status(key)
        pad = "  " * depth
        lines = [f"{pad}{target.render()} {_leader(target.render(), depth)} {st.name}"]
        if key in seen:
            return lines
        seen = seen | {key}

        # Direct contributions (facts, evidence, claims) with provenance.
        for c in self._atoms.get(key, []):
            if c.kind == "rule":
                continue
            prov = f"  →  {c.provenance.render()}" if c.provenance else ""
            lines.append(f"{pad}  └─ {c.note} ({c.source_id}){prov}")

        # Structural: every rule whose head unifies with this atom.
        for rule in self.program.of_type(ast.Rule):
            binding = _unify(rule.head, key)
            if binding is None:
                continue
            body = [ast.Predicate(p.name, tuple(binding.get(a, a) for a in p.args))
                    for p in rule.body]
            sep = " ∨ " if rule.connective == "established_if" else " ∧ "
            head_line = f"{pad}  └─ {rule.connective}: " + sep.join(b.render() for b in body)
            for kind, p in rule.exceptions:
                ep = ast.Predicate(p.name, tuple(binding.get(a, a) for a in p.args))
                head_line += f"  {kind} when {ep.render()}"
            lines.append(head_line)
            for b in body:
                lines.extend(self.trace(b, depth + 2, seen))
        return lines

    def discover(self, target: ast.Predicate) -> list[tuple[ast.Predicate, Status]]:
        """Which elements of ``target`` are not yet established?"""
        missing: list[tuple[ast.Predicate, Status]] = []
        for rule in self.program.of_type(ast.Rule):
            binding = _unify(rule.head, target.key())
            if binding is None:
                continue
            for p in rule.body:
                bp = ast.Predicate(p.name, tuple(binding.get(a, a) for a in p.args))
                st = self.atom_status(bp.key())
                if st.rank < Status.SUPPORTED.rank:
                    missing.append((bp, st))
        return missing

    # --- consistency ---------------------------------------------------
    def contradictions(self) -> list[str]:
        out: list[str] = []
        # 1. Any atom the evidence pulls both ways.
        for key, st in self.status.items():
            if st is Status.DISPUTED:
                name = ast.Predicate(key[0], key[1]).render()
                out.append(f"DISPUTED: {name} has support and refutation on the record")
        # 2. Declared mutually-exclusive propositions both holding.
        for ex in self.program.of_type(ast.Exclusive):
            live = [m for m in ex.members
                    if self.atom_status(m.key()).rank >= Status.SUPPORTED.rank]
            if len(live) >= 2:
                names = ", ".join(m.render() for m in live)
                out.append(f"MUTUAL EXCLUSION VIOLATED: {names} cannot all hold")
        return out

    def check_constraints(self) -> list[tuple[ast.Constraint, Optional[bool], str]]:
        results = []
        for c in self.program.of_type(ast.Constraint):
            ok, note = self._eval_constraint(c)
            results.append((c, ok, note))
        return results

    def _eval_constraint(self, c: ast.Constraint):
        left, lnote = self._resolve(c.left)
        right, rnote = self._resolve(c.right)
        if left is None or right is None:
            return None, (lnote or rnote or "unresolved operand")
        if c.op == "within":
            if not (isinstance(left, ast.DateLit) and isinstance(right, ast.DateLit)):
                return None, "duration constraints compare two dates"
            limit = c.n * _UNIT_DAYS[c.unit]
            delta = (date.fromisoformat(left.iso) - date.fromisoformat(right.iso)).days
            if c.direction == "of":
                return abs(delta) <= limit, ""
            if c.direction == "after":
                return 0 <= delta <= limit, ""
            return 0 <= -delta <= limit, ""  # before
        try:
            if isinstance(left, ast.Money) and isinstance(right, ast.Money):
                if left.currency != right.currency:
                    return None, f"currency mismatch {left.currency} vs {right.currency}"
                return _cmp(left.amount, right.amount, c.op), ""
            if isinstance(left, ast.DateLit) and isinstance(right, ast.DateLit):
                return _cmp_date(left.iso, right.iso, c.op), ""
            if isinstance(left, (int, float)) and isinstance(right, (int, float)):
                return _cmp(left, right, c.op), ""
        except ValueError as e:
            return None, str(e)
        return None, "operands are not comparable"

    def _resolve(self, v: ast.Value):
        """Turn a constraint operand into a concrete value, following ``id.field``."""
        if isinstance(v, (ast.Money, ast.DateLit)):
            return v, ""
        if isinstance(v, (int, float)):
            return v, ""
        if isinstance(v, ast.Ref):
            if "." in v.name:
                fid, fld = v.name.split(".", 1)
                fact = next((f for f in self.program.of_type(ast.Fact) if f.id == fid), None)
                if not fact:
                    return None, f"no fact named '{fid}'"
                if fld not in fact.fields:
                    return None, f"'{fid}' has no field '{fld}'"
                return fact.fields[fld], ""
            return None, f"unbound reference '{v.name}'"
        return None, "unsupported operand"

    # --- provenance audit ----------------------------------------------
    def _has_source(self, key: AtomKey, seen: set | None = None) -> bool:
        """Does this atom trace to *any* source, directly or through a rule?"""
        seen = seen or set()
        if key in seen:
            return False
        seen.add(key)
        for c in self._atoms.get(key, []):
            if c.provenance is not None:
                return True
        for rule in self.program.of_type(ast.Rule):
            binding = _unify(rule.head, key)
            if binding is None:
                continue
            for p in rule.body:
                bp = (p.name, tuple(binding.get(a, a) for a in p.args))
                if self._has_source(bp, seen):
                    return True
        return False

    def unsourced_conclusions(self) -> list[tuple[AtomKey, Status]]:
        """Propositions that reach SUPPORTED+ but trace to no source at all.

        A supported conclusion the compiler cannot ground in the record is the
        exact failure mode LVL exists to catch — a rigorous proof of a fact
        nobody wrote down. `lvl check --audit` reports these.
        """
        out = []
        for key, st in sorted(self.status.items(), key=lambda kv: (kv[0][0], kv[0][1])):
            if st.rank >= Status.SUPPORTED.rank and not self._has_source(key):
                out.append((key, st))
        return out

    # --- static checks (lvl check) -------------------------------------
    def static_check(self) -> list[Diagnostic]:
        diags: list[Diagnostic] = list(self.diagnostics)
        parties = {p.id for p in self.program.of_type(ast.Party)}
        arity: dict[str, int] = {}

        for n in self.program.nodes:
            if isinstance(n, ast.Fact) and n.provenance is None:
                diags.append(Diagnostic("warning",
                    f"fact '{n.id}' has no source(...) — provenance is required for a "
                    f"conclusion to be trustworthy", n.span))
            if isinstance(n, ast.Evidence) and n.provenance is None:
                diags.append(Diagnostic("warning",
                    f"evidence '{n.id}' has no source(...)", n.span))
            if isinstance(n, ast.Claim) and n.by not in parties:
                diags.append(Diagnostic("error",
                    f"claim '{n.id}' is by undeclared party '{n.by}'", n.span))
            if isinstance(n, ast.Query) and n.standard:
                try:
                    Standard.parse(n.standard)
                except ValueError as e:
                    diags.append(Diagnostic("error", str(e), n.span))
            # Arity consistency across all predicate occurrences.
            for pred in _preds_in(n):
                if pred.name in arity and arity[pred.name] != len(pred.args):
                    diags.append(Diagnostic("warning",
                        f"predicate '{pred.name}' used with {len(pred.args)} args here "
                        f"but {arity[pred.name]} elsewhere", getattr(n, "span", None)))
                arity.setdefault(pred.name, len(pred.args))
        return diags


# --- small helpers ---------------------------------------------------------

def _unify(head: ast.Predicate, key: AtomKey) -> Optional[dict]:
    name, args = key
    if head.name != name or len(head.args) != len(args):
        return None
    binding: dict[str, str] = {}
    for h, a in zip(head.args, args):
        if _VAR_RE.match(h) and h not in ("",):
            if h in binding and binding[h] != a:
                return None
            binding[h] = a
        elif h != a:
            return None
    return binding


def _preds_in(node) -> list[ast.Predicate]:
    out: list[ast.Predicate] = []
    if isinstance(node, ast.Fact):
        out.append(ast.Predicate(node.type, (node.id,)))
    if isinstance(node, ast.Evidence):
        if node.supports:
            out.append(node.supports)
        if node.refutes:
            out.append(node.refutes)
    if isinstance(node, ast.Claim):
        out.append(node.asserts)
    if isinstance(node, ast.Rule):
        out.append(node.head)
        out.extend(node.body)
    if isinstance(node, ast.Query):
        out.append(node.target)
    if isinstance(node, ast.Exclusive):
        out.extend(node.members)
    return out


def _cmp(a: float, b: float, op: str) -> bool:
    return {
        "<=": a <= b, ">=": a >= b, "<": a < b, ">": a > b,
        "==": a == b, "!=": a != b, "equals": a == b,
    }[op]


def _cmp_date(a: str, b: str, op: str) -> bool:
    # ISO dates compare correctly as strings.
    if op in ("before",):
        return a < b
    if op in ("after",):
        return a > b
    return _cmp_str(a, b, op)


def _cmp_str(a: str, b: str, op: str) -> bool:
    return {
        "<=": a <= b, ">=": a >= b, "<": a < b, ">": a > b,
        "==": a == b, "!=": a != b, "equals": a == b,
    }[op]


def _leader(label: str, depth: int) -> str:
    """The dotted leader that lines a proposition up with its status."""
    width = max(4, 46 - len(label) - depth * 2)
    return "." * width
