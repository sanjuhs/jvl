"""Compare two LVL programs.

This is the heart of the user's core ask: *given two legal documents as programs,
do they mean the same thing, and if not, what changed?*

Two notions:

* ``diff``  — a structural + semantic delta: which parties/facts/rules/
  obligations were added, removed, or changed, and which propositions ended up
  with a different status.
* ``equiv`` — semantic equivalence: do the two programs derive the *same
  conclusions*? Equivalence is defined over the derived epistemic state (the
  status of every proposition), not over surface syntax — so reordering, comments
  and formatting never matter, but a changed obligation does.

Limitation (documented, on the roadmap): equivalence keys propositions by name
and arguments, so two contracts that use *different entity ids* for the same role
will register as different. This is exactly right for comparing versions of the
same contract (the common case) and is a false negative for renamed-but-identical
ones; canonical renaming/normalisation is Phase 2 future work.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from . import ast
from .evaluator import Evaluator


@dataclass
class Diff:
    parties_added: list[str] = field(default_factory=list)
    parties_removed: list[str] = field(default_factory=list)
    facts_added: list[str] = field(default_factory=list)
    facts_removed: list[str] = field(default_factory=list)
    fact_changes: list[str] = field(default_factory=list)      # human-readable
    rules_added: list[str] = field(default_factory=list)
    rules_removed: list[str] = field(default_factory=list)
    rule_changes: list[str] = field(default_factory=list)
    obligations_added: list[str] = field(default_factory=list)
    obligations_removed: list[str] = field(default_factory=list)
    status_changes: list[str] = field(default_factory=list)    # the semantic delta
    props_added: list[str] = field(default_factory=list)
    props_removed: list[str] = field(default_factory=list)

    def is_empty(self) -> bool:
        return not any(vars(self).values())

    def as_dict(self) -> dict[str, Any]:
        return {k: v for k, v in vars(self).items() if v}


def _by_id(nodes) -> dict[str, Any]:
    return {n.id: n for n in nodes}


def _fact_signature(f: ast.Fact) -> dict[str, str]:
    from .parser import render_arg
    sig = {"type": f.type, "status": f.status_kw}
    for k, v in f.fields.items():
        sig[k] = render_arg(v)
    return sig


def _rule_signature(r: ast.Rule) -> str:
    body = " , ".join(sorted(b.render() for b in r.body))
    return f"{r.head.render()} {r.connective} {body}"


def diff(a: Evaluator, b: Evaluator) -> Diff:
    """Compute a structural + semantic diff from program ``a`` to program ``b``."""
    d = Diff()

    pa, pb = _by_id(a.program.of_type(ast.Party)), _by_id(b.program.of_type(ast.Party))
    d.parties_added = sorted(pb.keys() - pa.keys())
    d.parties_removed = sorted(pa.keys() - pb.keys())

    fa, fb = _by_id(a.program.of_type(ast.Fact)), _by_id(b.program.of_type(ast.Fact))
    d.facts_added = sorted(fb.keys() - fa.keys())
    d.facts_removed = sorted(fa.keys() - fb.keys())
    for fid in sorted(fa.keys() & fb.keys()):
        sa, sb = _fact_signature(fa[fid]), _fact_signature(fb[fid])
        for k in sorted(set(sa) | set(sb)):
            if sa.get(k) != sb.get(k):
                d.fact_changes.append(f"{fid}.{k}: {sa.get(k)!r} → {sb.get(k)!r}")

    ra = {r.id: _rule_signature(r) for r in a.program.of_type(ast.Rule)}
    rb = {r.id: _rule_signature(r) for r in b.program.of_type(ast.Rule)}
    d.rules_added = sorted(rb.keys() - ra.keys())
    d.rules_removed = sorted(ra.keys() - rb.keys())
    for rid in sorted(ra.keys() & rb.keys()):
        if ra[rid] != rb[rid]:
            d.rule_changes.append(f"{rid}: {ra[rid]}  →  {rb[rid]}")

    oa, ob = _by_id(a.program.of_type(ast.Obligation)), _by_id(b.program.of_type(ast.Obligation))
    d.obligations_added = sorted(ob.keys() - oa.keys())
    d.obligations_removed = sorted(oa.keys() - ob.keys())

    # The semantic delta: how the derived status of each proposition changed.
    keys = set(a.status) | set(b.status)
    for key in sorted(keys, key=lambda k: (k[0], k[1])):
        prop = ast.Predicate(key[0], key[1]).render()
        in_a, in_b = key in a.status, key in b.status
        if in_a and in_b:
            if a.status[key] is not b.status[key]:
                d.status_changes.append(
                    f"{prop}: {a.status[key].name} → {b.status[key].name}")
        elif in_b:
            d.props_added.append(f"{prop} ({b.status[key].name})")
        else:
            d.props_removed.append(f"{prop} ({a.status[key].name})")
    return d


@dataclass
class Equivalence:
    equivalent: bool
    discriminating: list[str] = field(default_factory=list)  # props that differ

    def as_dict(self) -> dict[str, Any]:
        return {"equivalent": self.equivalent, "discriminating": self.discriminating}


def equiv(a: Evaluator, b: Evaluator) -> Equivalence:
    """Do the two programs mean the same thing?

    Meaning, here, is both *what follows* (the derived status of every
    proposition) and *the operative terms* (the objective facts and the rules).
    Two programs are equivalent iff they agree on all of it. The discriminating
    list names exactly what breaks equivalence — the machine-checkable answer to
    "where do these two contracts actually differ in meaning?".

    Deliberately ignored as cosmetic: ordering, comments, whitespace, party
    display labels, node ids that don't change the logic. Those never appear in
    the diff this is built on, so they never break equivalence.
    """
    d = diff(a, b)
    disc: list[str] = []
    disc += [f"proposition status changed — {s}" for s in d.status_changes]
    disc += [f"proposition only in second — {s}" for s in d.props_added]
    disc += [f"proposition only in first — {s}" for s in d.props_removed]
    disc += [f"term changed — {s}" for s in d.fact_changes]
    disc += [f"fact only in second — {s}" for s in d.facts_added]
    disc += [f"fact only in first — {s}" for s in d.facts_removed]
    disc += [f"rule added — {s}" for s in d.rules_added]
    disc += [f"rule removed — {s}" for s in d.rules_removed]
    disc += [f"rule changed — {s}" for s in d.rule_changes]
    disc += [f"obligation added — {s}" for s in d.obligations_added]
    disc += [f"obligation removed — {s}" for s in d.obligations_removed]
    disc += [f"party added — {s}" for s in d.parties_added]
    disc += [f"party removed — {s}" for s in d.parties_removed]
    return Equivalence(equivalent=not disc, discriminating=disc)
