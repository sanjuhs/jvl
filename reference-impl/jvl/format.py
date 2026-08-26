"""Canonical formatter — pretty-print a parsed program back to canonical JVL.

A language that language models write needs a canonical form, so that two
equivalent programs render identically and diffs stay clean. `jvl fmt` parses a
program and re-emits it in this canonical style. The formatter is round-trip
safe: parsing the formatted output yields the same AST (see the round-trip test).
"""

from __future__ import annotations

from . import ast


def _money(m: ast.Money) -> str:
    # Group thousands with underscores, JVL-style.
    whole = f"{m.amount:,.0f}".replace(",", "_")
    return f"{m.currency} {whole}"


def _value(v: ast.Value) -> str:
    if isinstance(v, ast.Ref):
        return v.name
    if isinstance(v, ast.Money):
        return _money(v)
    if isinstance(v, ast.DateLit):
        return v.iso
    if isinstance(v, ast.Predicate):
        return _pred(v)
    if isinstance(v, str):
        return '"' + v.replace('"', '\\"') + '"'
    if isinstance(v, float):
        return str(int(v)) if v.is_integer() else str(v)
    return str(v)


def _pred(p: ast.Predicate) -> str:
    return f"{p.name}({', '.join(p.args)})"


def _provenance(p: ast.Provenance) -> str:
    parts = []
    if p.doc is not None:
        parts.append(f'doc="{p.doc}"')
    if p.page is not None:
        parts.append(f"page={p.page}")
    if p.para is not None:
        parts.append(f"para={p.para}")
    if p.exhibit is not None:
        parts.append(f'exhibit="{p.exhibit}"')
    if p.speaker is not None:
        parts.append(f'speaker="{p.speaker}"')
    return "from source(" + ", ".join(parts) + ")"


def _record(fields: dict[str, ast.Value]) -> str:
    if not fields:
        return "{ }"
    if len(fields) == 1:
        (k, v), = fields.items()
        return "{ " + f"{k}: {_value(v)}" + " }"
    inner = "\n".join(f"    {k}: {_value(v)}" for k, v in fields.items())
    return "{\n" + inner + "\n}"


def _format_node(n: ast.Node) -> str:
    if isinstance(n, ast.Jurisdiction):
        return f"jurisdiction {n.name}"
    if isinstance(n, ast.Party):
        return f'party {n.id} = {n.type} "{n.label}"'
    if isinstance(n, ast.Fact):
        s = f"fact {n.id} : {n.type} {_record(n.fields)}"
        if n.provenance:
            s += " " + _provenance(n.provenance)
        s += f" status {n.status_kw}"
        return s
    if isinstance(n, ast.Evidence):
        s = f"evidence {n.id} : {n.type} {_record(n.fields)}"
        if n.provenance:
            s += " " + _provenance(n.provenance)
        if n.supports:
            s += f" supports {_pred(n.supports)}"
        elif n.refutes:
            s += f" refutes {_pred(n.refutes)}"
        return s
    if isinstance(n, ast.Claim):
        return f'claim {n.id} by {n.by} : "{n.text}" asserts {_pred(n.asserts)}'
    if isinstance(n, ast.Rule):
        lines = [f"rule {n.id}:"]
        lines.append(f"    {_pred(n.head)} {n.connective}")
        if n.connective == "established_if":
            body = [f"        {_pred(n.body[0])}"] + [f"        or {_pred(b)}" for b in n.body[1:]]
        else:
            body = [f"        {_pred(b)}" for b in n.body]
        lines.extend(body)
        for ex in n.exceptions:
            lines.append(f"    except when {_pred(ex)}")
        return "\n".join(lines)
    if isinstance(n, ast.Obligation):
        fields = {"bearer": ast.Ref(n.bearer)}
        if n.counterparty:
            fields["to"] = ast.Ref(n.counterparty)
        fields["that"] = n.that
        if n.by_date:
            fields["by"] = n.by_date
        if n.on_breach:
            fields["on_breach"] = n.on_breach
        return f"{n.modality} {n.id} {_record(fields)}"
    if isinstance(n, ast.Constraint):
        if n.op == "within":
            return (f"constraint {n.id}: {_value(n.left)} within {n.n} {n.unit} "
                    f"{n.direction} {_value(n.right)}")
        return f"constraint {n.id}: {_value(n.left)} {n.op} {_value(n.right)}"
    if isinstance(n, ast.Exclusive):
        return "exclusive { " + " ".join(_pred(m) for m in n.members) + " }"
    if isinstance(n, ast.Query):
        s = f"{n.kind} {_pred(n.target)}"
        if n.standard:
            s += f" under {n.standard}"
        if n.for_party:
            s += f" for {n.for_party}"
        return s
    return f"# <unformattable node: {type(n).__name__}>"


def format_program(prog: ast.Program) -> str:
    """Render a program in canonical JVL, with a blank line between statements."""
    return "\n\n".join(_format_node(n) for n in prog.nodes) + "\n"
