"""Emit an LVL program as canonical JSON or as a graph.

This is Phase 1 of the roadmap made concrete: an LVL program already *contains*
the facts, relationships, provenance, and derived conclusions, so it can produce
the JSON and graph layers itself rather than depending on a separate extractor.
The output is deterministic (sorted keys, stable ordering) so two runs — or two
machines — produce byte-identical results, which is what makes diffing reliable.
"""

from __future__ import annotations

import json
from typing import Any

from . import ast
from .evaluator import Evaluator


def _prov(p: ast.Provenance | None) -> dict[str, Any] | None:
    if p is None:
        return None
    d = {"doc": p.doc, "page": p.page, "para": p.para,
         "exhibit": p.exhibit, "speaker": p.speaker}
    return {k: v for k, v in d.items() if v is not None} or None


def _value(v: ast.Value) -> Any:
    if isinstance(v, ast.Ref):
        return {"ref": v.name}
    if isinstance(v, ast.Money):
        return {"currency": v.currency, "amount": v.amount}
    if isinstance(v, ast.DateLit):
        return {"date": v.iso}
    if isinstance(v, ast.Predicate):
        return {"pred": v.render()}
    return v


def to_dict(ev: Evaluator) -> dict[str, Any]:
    """Canonical dictionary form of an evaluated program."""
    prog = ev.program

    atoms = []
    for key in sorted(ev.status, key=lambda k: (k[0], k[1])):
        name, args = key
        contribs = ev._atoms.get(key, [])
        atoms.append({
            "proposition": ast.Predicate(name, args).render(),
            "name": name,
            "args": list(args),
            "status": ev.status[key].name,
            "rank": ev.status[key].rank,
            "sources": sorted({
                c.provenance.render() for c in contribs if c.provenance
            }),
            "from": sorted({c.kind for c in contribs}),
        })

    parties = [{"id": p.id, "type": p.type, "label": p.label}
               for p in prog.of_type(ast.Party)]
    facts = [{"id": f.id, "type": f.type, "status": f.status_kw,
              "fields": {k: _value(v) for k, v in f.fields.items()},
              "source": _prov(f.provenance)}
             for f in prog.of_type(ast.Fact)]
    rules = [{"id": r.id, "head": r.head.render(),
              "connective": r.connective,
              "body": [b.render() for b in r.body]}
             for r in prog.of_type(ast.Rule)]
    obligations = [{"id": o.id, "modality": o.modality, "bearer": o.bearer,
                    "counterparty": o.counterparty, "that": o.that.render(),
                    "by": o.by_date.iso if o.by_date else None,
                    "on_breach": o.on_breach.render() if o.on_breach else None}
                   for o in prog.of_type(ast.Obligation)]
    constraints = []
    for c, ok, note in ev.check_constraints():
        constraints.append({"id": c.id, "op": c.op,
                            "left": _value(c.left), "right": _value(c.right),
                            "holds": ok, "note": note})

    return {
        "jurisdiction": next((j.name for j in prog.of_type(ast.Jurisdiction)), None),
        "parties": sorted(parties, key=lambda x: x["id"]),
        "facts": sorted(facts, key=lambda x: x["id"]),
        "rules": sorted(rules, key=lambda x: x["id"]),
        "obligations": sorted(obligations, key=lambda x: x["id"]),
        "constraints": sorted(constraints, key=lambda x: x["id"]),
        "atoms": atoms,
        "contradictions": ev.contradictions(),
    }


def to_json(ev: Evaluator, indent: int = 2) -> str:
    return json.dumps(to_dict(ev), indent=indent, sort_keys=False, ensure_ascii=False)


def to_graph(ev: Evaluator) -> dict[str, Any]:
    """A node/edge graph of the case: atoms, parties, and how they connect."""
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    seen: set[str] = set()

    def node(nid: str, kind: str, **extra):
        if nid in seen:
            return
        seen.add(nid)
        nodes.append({"id": nid, "kind": kind, **extra})

    for p in ev.program.of_type(ast.Party):
        node(p.id, "party", label=p.label, type=p.type)

    for key, st in ev.status.items():
        prop = ast.Predicate(key[0], key[1]).render()
        node(prop, "atom", status=st.name)

    # Rule edges: head depends on each body element.
    for r in ev.program.of_type(ast.Rule):
        head = r.head.render()
        node(head, "atom")
        for b in r.body:
            node(b.render(), "atom")
            edges.append({"from": head, "to": b.render(),
                         "rel": r.connective, "rule": r.id})

    # Evidence / claim edges.
    for e in ev.program.of_type(ast.Evidence):
        if e.supports:
            edges.append({"from": e.id, "to": e.supports.render(), "rel": "supports"})
            node(e.id, "evidence")
        if e.refutes:
            edges.append({"from": e.id, "to": e.refutes.render(), "rel": "refutes"})
            node(e.id, "evidence")
    for c in ev.program.of_type(ast.Claim):
        node(c.id, "claim", by=c.by)
        edges.append({"from": c.id, "to": c.asserts.render(), "rel": "claims"})

    return {"nodes": nodes, "edges": edges}


def to_dot(ev: Evaluator) -> str:
    """Graphviz DOT rendering, for a quick visual of the case."""
    g = to_graph(ev)
    palette = {"party": "#6366f1", "atom": "#0ea5e9", "evidence": "#10b981",
               "claim": "#f59e0b"}
    lines = ["digraph LVL {", '  rankdir=LR;', '  node [style=filled, fontname="Helvetica"];']
    for n in g["nodes"]:
        color = palette.get(n["kind"], "#94a3b8")
        label = n["id"].replace('"', '\\"')
        lines.append(f'  "{label}" [fillcolor="{color}22", color="{color}"];')
    for e in g["edges"]:
        lines.append(f'  "{e["from"]}" -> "{e["to"]}" [label="{e["rel"]}"];')
    lines.append("}")
    return "\n".join(lines)
