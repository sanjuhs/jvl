"""``lvl`` command-line interface.

Subcommands:

    lvl check    FILE                 parse + static checks + provenance audit
    lvl assert   FILE                 run every assert/refute in the file
    lvl explain  FILE "Pred(x)"       derivation trace for one proposition
    lvl discover FILE "Pred(x)"       what is still missing to establish it
    lvl check-contradictions FILE     report conflicts between clauses
    lvl constraints FILE              evaluate the objective constraints
    lvl simulate FILE --without ID    counterfactual: drop a node, re-run asserts
    lvl emit     FILE json|graph|dot  emit the program as data (the JSON/graph layer)
    lvl diff     A B                  structural + semantic diff of two programs
    lvl equiv    A B                  do two programs mean the same thing?
    lvl ask      FILE "question"      answer an English question (LLM picks the
                                      query; the engine computes the answer)
"""

from __future__ import annotations

import argparse
import sys

import json

from . import ast
from . import compare, format as fmt, nl, serialize
from .evaluator import Evaluator
from .lattice import Standard
from .parser import ParseError, parse


def _load(path: str) -> ast.Program:
    with open(path, "r", encoding="utf-8") as fh:
        return parse(fh.read())


def _predicate(text: str) -> ast.Predicate:
    prog = parse(f"explain {text}")
    return prog.of_type(ast.Query)[0].target


def _drop(program: ast.Program, node_id: str) -> ast.Program:
    kept = [n for n in program.nodes if getattr(n, "id", None) != node_id]
    return ast.Program(nodes=kept)


# --- commands --------------------------------------------------------------

def cmd_check(args) -> int:
    prog = _load(args.file)
    ev = Evaluator(prog).build()
    diags = ev.static_check()
    errors = [d for d in diags if d.level == "error"]
    for d in diags:
        print(d.render())
    counts = f"{len(errors)} error(s), {len(diags) - len(errors)} warning(s)"
    print(f"\n{'✗' if errors else '✓'} {args.file}: {counts}")
    if getattr(args, "audit", False):
        unsourced = ev.unsourced_conclusions()
        print("\n── provenance audit ──")
        if not unsourced:
            print("  ✓ every supported conclusion traces to a source")
        else:
            for key, st in unsourced:
                print(f"  ⚠ {ast.Predicate(key[0], key[1]).render()} is {st.name} "
                      f"but traces to no source")
    return 1 if errors else 0


def cmd_assert(args) -> int:
    prog = _load(args.file)
    ev = Evaluator(prog).build()
    queries = [q for q in prog.of_type(ast.Query) if q.kind in ("assert", "refute")]
    if not queries:
        print("no assert/refute statements in file")
        return 0
    failed = 0
    for q in queries:
        std = Standard.parse(q.standard) if q.standard else Standard.BalanceOfProbabilities
        verdict = ev.run_assert(q.target, std)
        mark = "assert" if q.kind == "assert" else "refute"
        print(f"\n⚖  {mark}  {q.target.render()}   standard: {std.name}\n")
        for line in ev.trace(q.target):
            print("  " + line)
        want = "passes" if q.kind == "assert" else "is refuted"
        ok = verdict.passes if q.kind == "assert" else (verdict.status.name == "REFUTED")
        verdict_txt = "✓" if ok else "✗"
        print(f"\n  RESULT: {verdict.status.name}  {verdict_txt} "
              f"({'meets' if verdict.passes else 'does not meet'} {std.name})")
        others = _contesting_claims(prog, q.target)
        if others:
            print(f"  NOTE:   contested by {others}")
        failed += 0 if ok else 1
    return 1 if failed else 0


def cmd_explain(args) -> int:
    ev = Evaluator(_load(args.file)).build()
    target = _predicate(args.predicate)
    print(f"\n⚖  explain  {target.render()}\n")
    for line in ev.trace(target):
        print("  " + line)
    return 0


def cmd_discover(args) -> int:
    ev = Evaluator(_load(args.file)).build()
    target = _predicate(args.predicate)
    missing = ev.discover(target)
    print(f"\n⚖  discover  what is missing for {target.render()}\n")
    if not missing:
        print("  nothing missing — every element is at least SUPPORTED")
        return 0
    for pred, st in missing:
        print(f"  ✗ {pred.render()} — {st.name}")
    return 0


def cmd_contradictions(args) -> int:
    ev = Evaluator(_load(args.file)).build()
    issues = ev.contradictions()
    print(f"\n⚖  contradiction check: {args.file}\n")
    if not issues:
        print("  ✓ no contradictions detected among the clauses")
        return 0
    for issue in issues:
        print(f"  ⚠ {issue}")
    return 1


def cmd_constraints(args) -> int:
    ev = Evaluator(_load(args.file)).build()
    results = ev.check_constraints()
    print(f"\n⚖  objective constraints: {args.file}\n")
    if not results:
        print("  (no constraints declared)")
        return 0
    bad = 0
    for c, ok, note in results:
        if ok is None:
            print(f"  ? {c.id}: {c.left} {c.op} {c.right} — {note}")
        elif ok:
            print(f"  ✓ {c.id}: holds")
        else:
            print(f"  ✗ {c.id}: VIOLATED")
            bad += 1
    return 1 if bad else 0


def cmd_simulate(args) -> int:
    prog = _load(args.file)
    print(f"\n⚖  simulate: {args.file}  (without '{args.without}')\n")
    base = Evaluator(prog).build()
    alt = Evaluator(_drop(prog, args.without)).build()
    for q in [q for q in prog.of_type(ast.Query) if q.kind in ("assert", "refute")]:
        b = base.atom_status(q.target.key()).name
        a = alt.atom_status(q.target.key()).name
        change = "" if a == b else f"   ← changed from {b}"
        print(f"  {q.target.render()}: {a}{change}")
    return 0


def cmd_emit(args) -> int:
    ev = Evaluator(_load(args.file)).build()
    if args.format == "json":
        print(serialize.to_json(ev))
    elif args.format == "graph":
        print(json.dumps(serialize.to_graph(ev), indent=2, ensure_ascii=False))
    elif args.format == "dot":
        print(serialize.to_dot(ev))
    return 0


def cmd_diff(args) -> int:
    a = Evaluator(_load(args.a)).build()
    b = Evaluator(_load(args.b)).build()
    d = compare.diff(a, b)
    if args.json:
        print(json.dumps(d.as_dict(), indent=2, ensure_ascii=False))
        return 0
    print(f"\n⚖  diff  {args.a}  →  {args.b}\n")
    if d.is_empty():
        print("  (identical — no structural or semantic differences)")
        return 0
    sections = [
        ("parties added", d.parties_added), ("parties removed", d.parties_removed),
        ("facts added", d.facts_added), ("facts removed", d.facts_removed),
        ("fact changes", d.fact_changes),
        ("rules added", d.rules_added), ("rules removed", d.rules_removed),
        ("rule changes", d.rule_changes),
        ("obligations added", d.obligations_added),
        ("obligations removed", d.obligations_removed),
        ("propositions added", d.props_added),
        ("propositions removed", d.props_removed),
        ("STATUS CHANGES (semantic delta)", d.status_changes),
    ]
    for title, items in sections:
        if not items:
            continue
        print(f"  {title}:")
        for it in items:
            mark = "±" if "→" in it or "vs" in it else ("+" if "added" in title else "-")
            print(f"    {mark} {it}")
        print()
    return 0


def cmd_equiv(args) -> int:
    a = Evaluator(_load(args.a)).build()
    b = Evaluator(_load(args.b)).build()
    result = compare.equiv(a, b)
    if args.json:
        print(json.dumps(result.as_dict(), indent=2, ensure_ascii=False))
        return 0 if result.equivalent else 1
    print(f"\n⚖  equiv  {args.a}  ≟  {args.b}\n")
    if result.equivalent:
        print("  ✓ EQUIVALENT — both programs derive the same conclusions")
        return 0
    print("  ✗ DIFFERENT — they diverge on these propositions:\n")
    for line in result.discriminating:
        print(f"    · {line}")
    return 1


def cmd_fmt(args) -> int:
    with open(args.file, "r", encoding="utf-8") as fh:
        src = fh.read()
    formatted = fmt.format_program(parse(src))
    if args.write:
        with open(args.file, "w", encoding="utf-8") as fh:
            fh.write(formatted)
        print(f"formatted {args.file}")
    else:
        print(formatted, end="")
    return 0


def cmd_ask(args) -> int:
    with open(args.file, "r", encoding="utf-8") as fh:
        src = fh.read()
    try:
        query_line = nl.question_to_query(src, args.question)
    except nl.NLError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    print(f'\n⚖  ask  "{args.question}"')
    print(f"   → the model chose the query:  {query_line}\n")
    try:
        q = parse(query_line).of_type(ast.Query)[0]
    except (ParseError, IndexError):
        print(f"error: the model produced something that isn't a valid query: {query_line!r}",
              file=sys.stderr)
        return 2
    ev = Evaluator(parse(src)).build()
    if q.kind in ("assert", "refute"):
        std = Standard.parse(q.standard) if q.standard else Standard.BalanceOfProbabilities
        verdict = ev.run_assert(q.target, std)
        for line in ev.trace(q.target):
            print("  " + line)
        print(f"\n  ANSWER: {verdict.status.name}  "
              f"({'meets' if verdict.passes else 'does not meet'} {std.name})")
    elif q.kind == "explain":
        for line in ev.trace(q.target):
            print("  " + line)
    elif q.kind == "discover":
        missing = ev.discover(q.target)
        if not missing:
            print("  nothing missing — every element is at least SUPPORTED")
        for pred, st in missing:
            print(f"  ✗ {pred.render()} — {st.name}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="lvl", description="Legal Verifiable Language compiler")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("check", help="parse + static checks + provenance audit")
    c.add_argument("file")
    c.add_argument("--audit", action="store_true",
                   help="also report supported conclusions that trace to no source")
    c.set_defaults(func=cmd_check)

    c = sub.add_parser("assert", help="run assert/refute statements")
    c.add_argument("file")
    c.set_defaults(func=cmd_assert)

    c = sub.add_parser("explain", help="derivation trace for a proposition")
    c.add_argument("file")
    c.add_argument("predicate")
    c.set_defaults(func=cmd_explain)

    c = sub.add_parser("discover", help="what is missing to establish a proposition")
    c.add_argument("file")
    c.add_argument("predicate")
    c.set_defaults(func=cmd_discover)

    c = sub.add_parser("check-contradictions", help="report conflicts between clauses")
    c.add_argument("file")
    c.set_defaults(func=cmd_contradictions)

    c = sub.add_parser("constraints", help="evaluate objective constraints")
    c.add_argument("file")
    c.set_defaults(func=cmd_constraints)

    c = sub.add_parser("simulate", help="counterfactual: drop a node and re-run")
    c.add_argument("file")
    c.add_argument("--without", required=True, metavar="ID")
    c.set_defaults(func=cmd_simulate)

    c = sub.add_parser("emit", help="emit the program as json / graph / dot")
    c.add_argument("file")
    c.add_argument("format", choices=["json", "graph", "dot"])
    c.set_defaults(func=cmd_emit)

    c = sub.add_parser("diff", help="structural + semantic diff of two programs")
    c.add_argument("a")
    c.add_argument("b")
    c.add_argument("--json", action="store_true")
    c.set_defaults(func=cmd_diff)

    c = sub.add_parser("equiv", help="do two programs mean the same thing?")
    c.add_argument("a")
    c.add_argument("b")
    c.add_argument("--json", action="store_true")
    c.set_defaults(func=cmd_equiv)

    c = sub.add_parser("ask", help="ask a plain-English question (needs ANTHROPIC_API_KEY)")
    c.add_argument("file")
    c.add_argument("question")
    c.set_defaults(func=cmd_ask)

    c = sub.add_parser("fmt", help="format a program in canonical LVL")
    c.add_argument("file")
    c.add_argument("--write", "-w", action="store_true", help="overwrite the file in place")
    c.set_defaults(func=cmd_fmt)
    return p


def _contesting_claims(prog: ast.Program, target: ast.Predicate) -> str:
    subject = set(target.args)
    others = []
    for cl in prog.of_type(ast.Claim):
        if cl.asserts.name == target.name and cl.asserts.args == target.args:
            continue
        if subject & set(cl.asserts.args):
            others.append(f"claim {cl.id} ({cl.by}: {cl.asserts.render()})")
    return "; ".join(others)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (ParseError, FileNotFoundError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
