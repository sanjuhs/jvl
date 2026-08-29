# Design Rationale — Why LVL is shaped the way it is

This document explains the *why* behind the language. If the [tour](02-language-tour.md)
teaches you to write LVL, this teaches you to argue with its designers.

## 1. Three representations, not one

The instinct when you first try to "computerise" a legal document is to reach for
one representation and force everything into it. That is the mistake. Legal
information wants to live in **three** layers at once, each good at something the
others are bad at:

| Representation | Best at | Weak at |
|---|---|---|
| **JSON extraction** | Capturing structured facts | Relationships, inference, what *follows* |
| **Knowledge / case graph** | Relationships, provenance, traversal | Precise executable semantics |
| **Executable program (LVL)** | Assertions, rules, proofs, counterfactuals | Harder to construct correctly |

LVL is the third layer. **It does not replace the other two — it sits on top of
them and gives them meaning you can execute.**

### JSON is great, and not enough

An extractor can pull this out of a case with high reliability:

```json
{ "payment": { "payer": "A", "receiver": "B", "amount": 1000000 },
  "claims": [ {"speaker": "A", "claim": "loan"},
              {"speaker": "B", "claim": "investment"} ] }
```

You can filter, search, and index it. But JSON does not know what *"loan"* means.
Ask "does B have a repayment obligation?" and there is no field for it — you need
logic the JSON cannot carry.

### A graph is better, and still not enough

A graph captures `WhatsApp17 —supports→ RepaymentObligation —applies_to→ B`, and
that is genuinely useful for "show me all evidence bearing on X". But what does
`supports` *mean*? That Y is true? More probable? Merely admissible? That some
lawyer argued it? The edge label hides exactly the semantics that matter.

### The program layer is where meaning becomes executable

```lvl
rule loan_definition:
    Loan(t) requires TransferOfValue(t) RepaymentObligation(t)
```

Now `supports` is not a vague edge; it is a typed contribution to a proposition's
epistemic status, and `Loan` is not a node but a rule you can *run*. That is a
different kind of operation from graph traversal — it is computation with a
result and an explanation.

> **The graph stores what the case says. The LVL program determines what follows
> from it.**

## 2. The compiler analogy

The cleanest way to see LVL's place: JSON and graphs are like an **AST** — real,
useful structure, but inert. LVL is the **language with semantics** layered over
that structure. An AST node `Assignment(x, 5)` is data; a language says what
running it *does*. LVL says what a legal structure *entails*.

## 3. Epistemic status as a first-class type

The single most important design decision. In most systems a fact is a boolean.
In law that is a lie. A proposition can be proven, merely supported, actively
disputed, asserted-but-unsupported, refuted, or simply unknown — and which one it
is *changes with the standard of proof you apply*.

So LVL makes status a value in a small lattice
(`Refuted < Unsupported < Unknown < Disputed < Supported < Proven`) and evaluates
every conclusion against a `Standard` (`BalanceOfProbabilities`,
`ClearAndConvincing`, `BeyondReasonableDoubt`). See [semantics](04-semantics.md).

This is what lets LVL *tolerate uncertainty instead of hiding it*. You are never
forced to write `dishonest_intention = true`. You write down the evidence, and
the system reports `Supported`, or `Unknown`, and refuses to certify the offence
if the standard is not met.

## 4. Provenance is mandatory

A formal system can be perfectly rigorous about a fact that an LLM hallucinated
during extraction. That is the nightmare, and it is why **every fact and piece of
evidence must carry a `source(...)`** back to `doc / page / paragraph / exhibit /
speaker`. The compiler warns on any fact without provenance. See
[the provenance model](05-provenance.md).

This also preserves the *chain of epistemology* that pure extraction flattens:

```
CLAIM (B: "I intended to repay")
   → supported by EVIDENCE (WhatsApp: "I'll repay next month")
      → permits INFERENCE (B treated it as repayable)
         → relevant to LEGAL PROPOSITION (a repayment obligation existed)
            → contributes to LEGAL CONCLUSION (the transaction was a loan)
```

LVL keeps every rung of that ladder addressable and traceable.

## 5. Deterministic to parse, easy for an LLM to emit

Two audiences must both read LVL unambiguously: a lawyer and a language model. So
the syntax is regular, block-structured, and **whitespace-insignificant** —
because whitespace-sensitive languages are exactly what models emit unreliably.
If a human and a model can disagree about what a line means, the syntax has
failed. This is a hard constraint, not an aesthetic preference; the entire
pipeline depends on a model being able to produce valid LVL. See [the LLM
kit](../llm/README.md).

## 6. Small core, rich libraries

The language has a handful of keywords. It ships almost no legal vocabulary.
Offences, contract types, and doctrines live in `.lvl` libraries
(`spec/stdlib/`) as ordinary rules — versioned, forkable, and arguable in public,
never compiled into the binary. A jurisdiction is a library, not a language fork.

## 7. Why not just use Prolog / Catala / L4?

We should borrow heavily from all of them (see [prior art](06-prior-art.md)), and
an early implementation could even *compile to* Prolog. But none of the existing
systems combines the three things LVL treats as central:

- **PROLEG** models allegations/evidence/exceptions beautifully — but truth is
  still essentially boolean, and provenance to a source PDF is not its concern.
- **Catala** turns legislation into executable code with elegant default logic —
  but it expects a human to encode statutes; it is not built for "drop a case
  file, get an executable world model with sources".
- **L4 / Yuho** are excellent at formalising *rules*; the case-file side, with
  epistemic status and provenance, is out of scope.

LVL's thesis is that **epistemic status + mandatory provenance + LLM-emittable
syntax**, together, is the combination nobody has shipped — and it is exactly the
combination the "case file → checkable program" pipeline needs.

## 8. The stack, drawn once

```
Graph  = memory        (what the case says, and how it connects)
JSON   = interchange    (extraction and transport)
LVL    = meaning        (typed propositions, rules, provenance)
Codex  = computation    (assert / explain / discover / simulate)
LLM    sits over all four, translating and narrating — never deciding.
```
