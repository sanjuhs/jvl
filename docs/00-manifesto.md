# The LVL Manifesto

*Why a language for law, and what it is careful never to become.*

## The problem

A contract, a statute, a judgment, a charge sheet — each is, in disguise, a
program about the world. It declares parties. It states facts. It sets
conditions. It derives obligations. It reaches conclusions. And yet it lives as
prose: impossible to run, painful to check, and endlessly arguable not because
the law is genuinely unclear but because *nobody can see the whole structure at
once*.

Everything else we consider serious, we make checkable. We type-check programs.
We unit-test bridges' load calculations. We formally verify avionics. Law — the
operating system of society — we still ship as unversioned natural language and
debug in courtrooms, one expensive exception at a time.

## The bet

**A legal document can be compiled into a program, and that program can be
statically checked.** Not the whole of law — law contains genuine ambiguity,
balancing tests, discretion, and moral judgement that no type system should
pretend to resolve. But *far more of it than we currently formalise*. Dates,
amounts, durations, and the logical skeleton of an argument — "the offence
requires A and B and C and D" — are structure we can capture, execute, and
audit.

LVL is a small language for writing that structure down, so a machine (or a
careful human) can ask:

- Does this obligation actually follow from these facts?
- Which element of this charge is unproven, and which is merely contested?
- Do these clauses contradict each other?
- What changes if we remove this exhibit, or amend this rule?
- Where does every single conclusion trace back to in the record?

## Three commitments

1. **Honesty about uncertainty.** A proposition in LVL is never just `true`. It
   carries an epistemic status and is judged against a standard of proof. The
   language refuses to let you assert a conclusion without saying how well it is
   supported. Law lives in doubt; the type system lives there too.

2. **Provenance or it didn't happen.** Every fact links back to a document, a
   page, a paragraph, a speaker. A conclusion the compiler cannot trace to the
   record is a defect it reports. This is the one non-negotiable guardrail
   against the failure mode that makes automated legal reasoning dangerous: a
   flawless proof of a hallucinated fact.

3. **Determinism where determinism is honest.** Given the same program, LVL
   produces the same answer, every time, with the same explanation. Where the
   law is genuinely determinate — arithmetic, temporal order, the logical form
   of a rule — we make it fully mechanical. Where it is not, LVL's job is to
   isolate exactly the human judgement that remains, and hand it to a human.

## What LVL is not

- **Not a robot judge.** LVL makes arguments explicit and checkable. It does not
  decide cases. Its output is a structured argument for a human to review, never
  a verdict.
- **Not legal advice.** It is a research tool. Nothing it emits should inform a
  real decision without a qualified human in the loop.
- **Not a replacement for the record.** The messy, information-rich layers — the
  raw text, the JSON extraction, the case graph — are kept underneath LVL, never
  discarded. See [the design rationale](01-design-rationale.md).
- **Not a claim that all of law is computable.** It is a claim that the
  *checkable part is much larger than we act as if it is*, and that isolating it
  is worth doing.

## Why open source, why MIT

Law belongs to everyone it governs. A language for encoding it should be forkable
by a legal aid clinic, a startup, a court, a student, and a sceptic — without
permission and without a licence fee. If LVL is wrong about something, the fix
should be a pull request, in public, where the reasoning can be argued with.

> Make the law's structure visible. Let humans keep the judgement.
