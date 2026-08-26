# The Central Thesis — Transform vs. Decide, and Scale

This document states the single idea the whole project is a bet on, and gives an
honest answer to the obvious question: *is this actually possible?*

## 1. The separation of concerns

The most important design decision in JVL is not in the syntax. It is a division
of labour:

> **The LLM transforms. The program decides.**

An LLM is an *unreliable judge* but a *capable translator*. So JVL never asks a
model to weigh whether a fact is legally valid, whether an element is satisfied,
or who should win. It asks only for a faithful **translation**:

- document → JVL program
- natural-language question → JVL assertion

Then the assertion runs against the whole logic of the program, and the
**deterministic engine — not the model — returns the answer**, with a derivation
trace back to the record.

```
        ┌──────────────── the fuzzy part (LLM) ────────────────┐
        │  read an arbitrary document  →  emit a JVL program    │
        │  read a question in English  →  emit an assertion     │
        └───────────────────────────────┬──────────────────────┘
                                         ▼
        ┌────────────── the exact part (compiler) ─────────────┐
        │  run the assertion over every rule and fact           │
        │  return proven / refuted / disputed — deterministically│
        │  show the derivation, sourced to the document          │
        └───────────────────────────────────────────────────────┘
```

Why this matters: the failure mode of "just ask the LLM if B has to repay A" is
that the model's answer is a confident guess with no audit trail, different each
run. JVL moves the *judgement* into code you can read and re-run, and confines
the model to the one job it is genuinely good at — turning language into
structure. The model's output is even checkable: a program that doesn't parse,
or a fact with no `source(...)`, is rejected before any question is asked.

## 2. Scale is a feature, not a problem

Because a JVL program is *just a program*, it can be **arbitrarily large**. A
five-thousand-page case file, an entire contract suite, a constitution, a legal
treatise — each compresses into some number of typed propositions, rules, and
provenance links. There is no length limit; there is only more of the same.

And crucially, **an assertion still runs over all of it**. However big the
program gets, you can still ask:

- *Is this internally consistent?* (contradiction detection)
- *Is this clause violated, given these facts?* (`assert` / `constraint`)
- *Does this conclusion follow?* (derivation trace)
- *Do these two versions still mean the same thing?* (`equiv`)

These are questions you **cannot ask natural language at all**. Prose has no
notion of "consistent" or "follows". The moment the document is a program, an
entire class of checks becomes available that simply did not exist before.

This is the same leap every other serious field made: a bridge design became
checkable when it became equations; a circuit became verifiable when it became a
netlist. Law is unusual only in that we still ship it as un-runnable prose.

## 3. Is it possible? An honest assessment

**Yes for the checkable skeleton; no for the whole of law — and JVL is built to
respect that line.**

What is clearly tractable, and works in the reference implementation today:

- The *logical form* of an argument — "the offence requires A ∧ B ∧ C" — and
  propagating support up it.
- Objective relations — amounts, dates, durations, caps — as pure computation.
- Consistency and contradiction between clauses.
- Semantic comparison of two documents.

What is genuinely hard, and where the honesty lives:

1. **Faithful translation is the crux.** The whole thesis rests on the LLM
   producing a program that actually represents the document. This is a real,
   unsolved reliability problem. JVL's answer is not to pretend it's solved but
   to make errors *visible and checkable*: mandatory provenance means every fact
   can be audited against the source, and a future verification pass (a second
   model checking the encoding against the text) is a first-class roadmap item.
   The provenance layer exists precisely so that translation errors surface
   rather than hide.

2. **Open-textured law resists formalisation.** "Reasonable", "dishonest
   intention", "good faith" — these are balancing tests, not booleans. JVL does
   **not** fake a value here. It leaves the proposition `Unknown` or `Disputed`,
   and `discover` hands the precise open question to a human. The claim is never
   "all of law is computable"; it is "the checkable part is much larger than we
   act as if it is, and isolating it is worth doing."

3. **Garbage in, rigorous garbage out.** A perfect proof over a mis-extracted
   fact is dangerous. This is why provenance is mandatory and why JVL positions
   itself as a tool that *surfaces structure for human review*, never a robot
   judge.

So: cracking "compile an arbitrary document and answer any question" completely
and autonomously is **not** realistic, and we should distrust anyone who claims
it. But building a system where an LLM drafts a checkable, sourced program and a
deterministic engine answers precise questions over it — with the open questions
clearly marked for humans — is not only possible, it is largely working in this
repository at small scale. The research frontier is **reliability and coverage of
the translation step**, and that is exactly where the effort should go.

> The bet is not that machines can judge the law. It is that machines can make
> the law's structure *checkable*, and leave the judging to us.

See also: [the manifesto](00-manifesto.md), [design rationale](01-design-rationale.md),
and the [LLM kit](../llm/README.md) that operationalises the translation step.
