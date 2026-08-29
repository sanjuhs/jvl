# FAQ

**Is this trying to replace lawyers or judges?**
No. LVL makes the *structure* of a legal argument explicit and checkable so
humans can see it, audit it, and find holes in it faster. Every design choice —
mandatory provenance, `Disputed` never auto-resolving, `discover` handing open
questions back — exists to keep the judgement with a human. See the
[manifesto](00-manifesto.md).

**Isn't law too ambiguous to formalise?**
Parts of it, yes — and LVL deliberately does not formalise those. But a large
part of any legal document is *not* ambiguous: dates, amounts, durations, and the
logical form "the offence requires A and B and C." LVL captures that determinate
skeleton and leaves the genuinely open questions marked `UNKNOWN` for a human.
The claim is not "all law is code"; it is "far more of it is checkable than we
act as if it is."

**Why not just use JSON, or a knowledge graph?**
Use both — underneath LVL. JSON captures facts but not what follows; graphs
capture relationships but not precise semantics. LVL is the executable meaning
layer on top. Full argument in the [design rationale](01-design-rationale.md).

**Why invent a language instead of using Prolog / Catala / L4?**
We borrow heavily from all of them, and a future backend may compile LVL *to*
Prolog. But none combines epistemic status + mandatory provenance + an
LLM-emittable surface, which is exactly what the case-file pipeline needs. See
[prior art](06-prior-art.md).

**How does an LLM fit in?**
The LLM does the hard, fuzzy part — reading a messy document and drafting an LVL
program with honest sources. LVL then does the part LLMs are bad at: exact,
deterministic, checkable logic. The [`llm/`](../llm/README.md) folder is a full
kit for teaching a model to emit valid LVL, including a Claude skill.

**What stops the LLM from hallucinating a fact?**
Nothing stops it from *drafting* one — but the provenance requirement makes it
visible. A fact with a bogus `source(...)` is auditable against the real
document; a fact with no source is a compiler warning. LVL cannot verify the
world, but it makes every claim about the world traceable. See
[provenance](05-provenance.md).

**Is the output deterministic?**
Yes. Same program → same answer → same explanation, always. That is a core goal:
making the mechanical part of law actually mechanical. See
[semantics §8](04-semantics.md).

**Can it really find contradictions?**
Within a program, yes: conflicting evidence on one proposition becomes
`Disputed`, and `exclusive { ... }` sets are checked for mutual-exclusion
violations. `lvl check-contradictions` reports both. It cannot find
contradictions it was never told about — it reasons over what you encode.

**Why is the syntax whitespace-insignificant and so plain?**
Because two very different readers — a lawyer and a language model — must both
parse it unambiguously, and whitespace-sensitive grammars are exactly what models
get wrong. Plainness is a feature.

**What can I actually run today?**
Everything in [`examples/`](../examples/). Clone it, `pip install -e .` in
`reference-impl/`, and run `lvl assert examples/01-loan-vs-investment.lvl`.

**Is this legal advice / usable in a real matter?**
No. It is a research prototype. Its output must be reviewed by a qualified human
before it informs any real decision.

**What's the fastest way to help?**
Write a worked example from a domain you know, or a jurisdiction library in
`spec/stdlib/`. See the [roadmap](07-roadmap.md) and
[CONTRIBUTING](../CONTRIBUTING.md).
