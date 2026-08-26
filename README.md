<h1 align="center">JVL — Jhana Verifiable Law</h1>

<p align="center">
  <em>Compile a legal document into a program you can statically check.</em><br>
  <strong>Facts carry provenance. Claims carry an epistemic status. Arguments type-check.</strong>
</p>

<p align="center">
  <a href="#quickstart">Quickstart</a> ·
  <a href="docs/02-language-tour.md">Language Tour</a> ·
  <a href="docs/01-design-rationale.md">Why It Exists</a> ·
  <a href="docs/04-semantics.md">Semantics</a> ·
  <a href="llm/README.md">Teaching an LLM</a> ·
  <a href="docs/07-roadmap.md">Roadmap</a>
</p>

<p align="center">
  <code>MIT licensed</code> · <code>early / experimental</code> · <code>reference compiler in Python</code>
</p>

---

## The one-paragraph pitch

A contract or a case file is really a *program* about the world: it defines parties, states facts, sets conditions, derives obligations, and reaches conclusions. Today that program lives as prose — impossible to run, hard to check, easy to argue about. **JVL** is a small language that an LLM (or a lawyer) can translate a legal document into, so that the resulting program can be **compiled, statically checked, and queried**: *Does this obligation actually follow? Which element of the offence is unproven? What breaks if we remove Exhibit P-17? Where does every conclusion trace back to in the source PDF?*

JVL is **not** a replacement for your JSON extractor or your case graph. It's the layer that gives them *meaning you can execute*. See [the design rationale](docs/01-design-rationale.md).

---

## What makes JVL different

Most "legal tech" either extracts structured JSON (great for facts, silent on *what follows*) or builds a knowledge graph (great for relationships, vague on *semantics*). JVL adds the third layer and keeps the other two:

| Layer | Representation | Answers |
|---|---|---|
| Extraction | JSON | *What does the document say?* |
| Memory | Case graph | *How is everything related?* |
| **Meaning** | **JVL program** | ***What follows? What's proven? What's missing?*** |

Three ideas do the heavy lifting, and as far as we can tell no existing legal DSL combines all three (see [prior art](docs/06-prior-art.md)):

1. **Epistemic status is a first-class type.** A proposition is never just `true`. It is `Proven`, `Supported`, `Disputed`, `Unsupported`, `Refuted`, or `Unknown`, evaluated against a **standard of proof** (`BalanceOfProbabilities`, `ClearAndConvincing`, `BeyondReasonableDoubt`). Law lives in uncertainty; the type system refuses to pretend otherwise.

2. **Provenance is mandatory, not decorative.** Every fact and every piece of evidence links back to `doc / page / paragraph / exhibit / speaker`. A conclusion you can't trace to the record is a compile-time warning. This is the guardrail against a rigorous proof of a **hallucinated** fact.

3. **Legal arguments type-check.** `assert Cheating(accused)` runs the rules, propagates statuses up an evidence lattice, and returns a **derivation trace** — which elements hold, which are missing, which are contested — instead of a bare yes/no. It's *static type checking for a legal argument*.

---

## A taste of the language

```jvl
jurisdiction IN.Contract.v1

party A = Person "Anil Kumar"
party B = Person "Beena Rao"

fact transfer_17 : TransferOfValue {
    from:   A
    to:     B
    amount: INR 1_000_000
    on:     2025-03-10
} from source(doc="BankStatement_3", page=2, para=4) status Established

claim c_loan   by A : "the transfer was a loan"       asserts Loan(transfer_17)
claim c_invest by B : "the transfer was an investment" asserts Investment(transfer_17)

evidence w17 : Message {
    author: B
    text:   "I'll repay you next month."
} from source(doc="WhatsApp_17", para=21) supports RepaymentObligation(transfer_17)

rule loan_definition:
    Loan(t) requires
        TransferOfValue(t)
        RepaymentObligation(t)

rule repayment_obligation:
    RepaymentObligation(t) established_if
        AdmittedRepayment(t)
        or ContractRequiresRepayment(t)

# Does the loan claim actually hold, on the balance of probabilities?
assert Loan(transfer_17) under BalanceOfProbabilities
```

Running it doesn't just say "true". It says *why*, and points at the record:

```
$ jvl assert examples/01-loan-vs-investment.jvl

⚖  assert  Loan(transfer_17)   standard: BalanceOfProbabilities

  Loan(transfer_17) ................................... SUPPORTED
  ├─ TransferOfValue(transfer_17) ..................... ESTABLISHED
  │     └─ BankStatement_3, p.2 ¶4
  └─ RepaymentObligation(transfer_17) ................. SUPPORTED
        └─ established_if AdmittedRepayment ∨ ContractRequiresRepayment
        └─ evidence w17 → WhatsApp_17 ¶21  ("I'll repay you next month.")

  RESULT: SUPPORTED  ✓ meets BalanceOfProbabilities
  NOTE:   contested by claim c_invest (B: "investment") — status is defeasible
```

Full walkthrough: **[the language tour](docs/02-language-tour.md)**.

---

## Quickstart

Requires Python 3.10+. No third-party dependencies for the core.

```bash
git clone https://github.com/sanjuhs/jvl.git
cd jvl/reference-impl
pip install -e .

# Type-check a program (parse + static checks + provenance audit)
jvl check ../examples/01-loan-vs-investment.jvl

# Evaluate the assertions inside a program and print derivation traces
jvl assert ../examples/01-loan-vs-investment.jvl

# Explain how a single proposition is (or isn't) established
jvl explain ../examples/01-loan-vs-investment.jvl "RepaymentObligation(transfer_17)"

# Counterfactual: re-run with a fact or piece of evidence removed
jvl simulate ../examples/01-loan-vs-investment.jvl --without w17
```

Not sure where to start? Read the [tour](docs/02-language-tour.md), then open [`examples/`](examples/).

---

## The pipeline JVL is built for

JVL is the top of a stack, and it never throws away the messy layers below it:

```
              LEGAL DOCUMENT (PDF, contract, judgment, filings)
                              │
                              ▼
                     LLM extraction  ──────────────►  raw text kept, always
                              │
              ┌───────────────┴───────────────┐
              ▼                                ▼
        structured JSON                    CASE GRAPH
     (facts, parties, dates)        (relationships, provenance)
              └───────────────┬───────────────┘
                              ▼
                      JVL  PROGRAM              ◄── this repository
              typed facts · epistemic status · rules · provenance
                              │
        ┌──────────────┬──────┴───────┬───────────────┐
        ▼              ▼              ▼               ▼
     assert         explain        discover        simulate
   prove/refute   derivation      what's missing   remove a fact /
   an element     trace           for a claim      change a rule, re-run
```

> **The graph stores what the case says. The JVL program determines what follows from it.**

The extraction step is where an LLM shines, and the [`llm/`](llm/README.md) folder is a complete kit — system prompt, extraction guide, few-shot examples, and a Claude Code skill — for teaching a model to emit valid JVL with honest provenance.

---

## Repository map

| Path | What's inside |
|---|---|
| [`docs/`](docs/) | Manifesto, design rationale, language tour, grammar, semantics, provenance model, prior-art survey, roadmap, FAQ |
| [`spec/`](spec/) | The EBNF grammar and the `stdlib` of core legal types & predicates |
| [`reference-impl/`](reference-impl/) | A working Python compiler: lexer, parser, epistemic evaluator, CLI |
| [`examples/`](examples/) | Annotated `.jvl` programs — loan-vs-investment, an NDA, a criminal-cheating charge |
| [`llm/`](llm/) | How to teach an LLM to write JVL, plus a ready-to-use Claude skill |

---

## Design principles

- **Deterministic to parse, easy for an LLM to emit.** Regular, block-structured syntax with low ambiguity. If a human lawyer and a language model disagree on what a line means, the syntax has failed.
- **Honest about uncertainty by construction.** You cannot write down a legal conclusion without also writing down how well it's supported and where it comes from.
- **Provenance or it didn't happen.** A conclusion with no traceable source is a defect the compiler reports.
- **Small core, rich standard library.** The language has a handful of keywords; jurisdictions, offences, and contract templates live in `.jvl` libraries, not in the compiler.
- **A tool for reasoning, not a robot judge.** JVL makes legal arguments explicit and checkable. It does not decide cases, and it is not legal advice. See [the manifesto](docs/00-manifesto.md).

---

## Status & how to help

This is an **early, experimental** project. The language will change. The reference implementation covers a meaningful subset end-to-end and is designed to be read and extended. Good first contributions: new worked examples in `examples/`, jurisdiction libraries in `spec/stdlib/`, and rough edges in the parser. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE). Use it, fork it, build a company on it.

---

<p align="center"><sub>JVL is a research prototype. It is not a lawyer, does not give legal advice, and its output must be reviewed by a qualified human before it informs any real decision.</sub></p>
