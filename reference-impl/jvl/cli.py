"""``jvl`` command-line interface.

Subcommands:

    jvl check    FILE                 parse + static checks + provenance audit
    jvl assert   FILE                 run every assert/refute in the file
    jvl explain  FILE "Pred(x)"       derivation trace for one proposition
    jvl discover FILE "Pred(x)"       what is still missing to establish it
    jvl check-contradictions FILE     report conflicts between clauses
    jvl constraints FILE              evaluate the objective constraints
    jvl simulate FILE --without ID    counterfactual: drop a node, re-run asserts
"""

from __future__ import annotations

import argparse
import sys

from . import ast
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


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="jvl", description="Jhana Verifiable Law compiler")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("check", help="parse + static checks + provenance audit")
    c.add_argument("file")
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
