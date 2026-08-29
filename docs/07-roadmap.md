# Roadmap

LVL is an early, experimental project. This is the honest state of it and where
it is heading. Nothing here is a promise; it is a direction, and pull requests
move it.

## Where v0.1 is today

**Working, end-to-end, in this repository:**

- Lexer, parser, and AST for the full v0.1 surface syntax.
- Forward-chaining evaluator with the epistemic lattice and standards of proof.
- `assert` / `prove` / `refute` with full derivation traces.
- `explain`, `discover` (missing-element analysis).
- Contradiction detection (evidential + declared `exclusive`).
- Objective `constraint` checking (money / date / number).
- `simulate --without` counterfactuals.
- Static checks: provenance audit, undeclared-party errors, arity warnings.
- Deontic nodes (`obligation` / `permission` / `prohibition`) parsed and modelled.
- Three worked examples and a passing test suite.

## Near term (v0.2)

- **First-class default logic:** `normally / except / except-to-exception`, the
  single most important missing construct — it is how statutes are actually
  written (borrow directly from Catala).
- **Provenance on inferences**, plus an `lvl check --audit` report listing every
  atom with no path to a source.
- **Richer constraints:** durations and intervals (`within 3 years`), currency
  conversion policy, arithmetic expressions.
- **Better diagnostics:** carry source spans through every error; suggest fixes.
- **`refute` and burden-of-proof semantics:** model which party bears the burden
  on each element, not just whether it is met.

## Medium term (v0.3+)

- **An `lvl fmt` canonical formatter** — essential for a language LLMs write, so
  diffs stay clean.
- **Compile-to-Prolog / ASP backend**, so hard queries can use a real solver, and
  LVL becomes the friendly front-end over proven engines (the SMU `dsl`
  philosophy).
- **LegalRuleML export**, for interchange with the wider legal-informatics world.
- **A language server (LSP):** hovers showing a proposition's current status,
  go-to-source, inline contradiction squiggles.
- **Graph bridge:** import a case graph directly into base atoms; export an LVL
  program's derivation as a graph.

## Longer term / research

- **Temporal reasoning:** obligations that arise, transfer, and expire over time.
- **Probabilistic / weighted evidence** as an optional layer above the discrete
  lattice, for "how strong is this really?" without faking precision.
- **Precedent and analogical reasoning** — where LVL most obviously ends and
  human judgement (assisted by an LLM) must take over.
- **A verification story:** given an LVL encoding and the source document, can a
  second model *check* that the encoding faithfully represents the text? The
  provenance layer is the foundation for exactly this.

## Non-goals

- Becoming a robot judge or issuing verdicts.
- Modelling the entirety of any legal system.
- Replacing the graph or JSON layers rather than sitting above them.
- Precision theatre — a fabricated number where the law is genuinely open.

## How to push it forward

The highest-leverage contributions right now are **worked examples** (real-ish
cases exercised end to end), **jurisdiction libraries** in `spec/stdlib/`, and
**parser hardening**. See [CONTRIBUTING.md](../CONTRIBUTING.md).
