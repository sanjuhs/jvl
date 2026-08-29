"""LVL MCP server — expose the LVL compiler as tools for LLMs and agents.

This lets Claude (or any MCP client) drive LVL as a set of tools: hand it a
program, ask it to check, assert, explain, discover, find contradictions, or
compare two programs. The model does the language work; LVL returns the
deterministic, sourced answer — the project's thesis, wired into the agent loop.

Run:
    pip install -e ../reference-impl
    pip install "mcp[cli]"
    python lvl_mcp.py           # stdio transport

Add to Claude Code / Claude Desktop: see README.md in this folder.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from lvl import Evaluator, compare, serialize
from lvl.ast import Query
from lvl.lattice import Standard
from lvl.parser import parse

mcp = FastMCP("lvl")


def _eval(program: str) -> Evaluator:
    return Evaluator(parse(program)).build()


def _predicate(text: str):
    return parse("explain " + text).of_type(Query)[0].target


@mcp.tool()
def check(program: str) -> str:
    """Parse an LVL program, type-check it, and audit facts for provenance.

    Returns the diagnostics (errors and warnings). Use this first when given a
    program you didn't write.
    """
    diags = _eval(program).static_check()
    if not diags:
        return "OK — no errors or warnings."
    return "\n".join(d.render() for d in diags)


@mcp.tool()
def assert_proposition(program: str, proposition: str,
                       standard: str = "BalanceOfProbabilities") -> str:
    """Does a proposition hold, to a standard of proof? Returns the derivation
    trace and the verdict. `proposition` is like "Loan(transfer_17)"; `standard`
    is BalanceOfProbabilities, ClearAndConvincing, or BeyondReasonableDoubt.
    """
    ev = _eval(program)
    target = _predicate(proposition)
    verdict = ev.run_assert(target, Standard.parse(standard))
    lines = ev.trace(target)
    lines.append("")
    lines.append(f"RESULT: {verdict.status.name} "
                 f"({'meets' if verdict.passes else 'does not meet'} {standard})")
    return "\n".join(lines)


@mcp.tool()
def explain(program: str, proposition: str) -> str:
    """Return the full derivation tree for a proposition, each leaf sourced to
    the record."""
    ev = _eval(program)
    return "\n".join(ev.trace(_predicate(proposition)))


@mcp.tool()
def discover(program: str, proposition: str) -> str:
    """Which elements of a proposition are still missing (not yet Supported)?"""
    ev = _eval(program)
    missing = ev.discover(_predicate(proposition))
    if not missing:
        return "Nothing missing — every element is at least SUPPORTED."
    return "\n".join(f"MISSING: {p.render()} — {s.name}" for p, s in missing)


@mcp.tool()
def contradictions(program: str) -> str:
    """Report internal conflicts: disputed propositions and violated exclusivity."""
    issues = _eval(program).contradictions()
    return "\n".join(issues) if issues else "No contradictions detected."


@mcp.tool()
def constraints(program: str) -> str:
    """Evaluate the objective money/date/number constraints in the program."""
    out = []
    for c, ok, note in _eval(program).check_constraints():
        out.append(f"{c.id}: " + ("holds" if ok else "VIOLATED" if ok is False else f"? {note}"))
    return "\n".join(out) if out else "No constraints declared."


@mcp.tool()
def emit_json(program: str) -> str:
    """Emit the whole program as canonical JSON — the data layer (parties, facts,
    atoms with status and provenance, rules, constraints)."""
    return serialize.to_json(_eval(program))


@mcp.tool()
def diff(program_a: str, program_b: str) -> str:
    """Structural + semantic diff between two LVL programs."""
    d = compare.diff(_eval(program_a), _eval(program_b))
    import json
    return json.dumps(d.as_dict(), indent=2) if not d.is_empty() else "Identical."


@mcp.tool()
def equiv(program_a: str, program_b: str) -> str:
    """Do two LVL programs mean the same thing? Names any diverging propositions."""
    r = compare.equiv(_eval(program_a), _eval(program_b))
    if r.equivalent:
        return "EQUIVALENT — both programs derive the same conclusions."
    return "DIFFERENT:\n" + "\n".join("  · " + d for d in r.discriminating)


if __name__ == "__main__":
    mcp.run()
