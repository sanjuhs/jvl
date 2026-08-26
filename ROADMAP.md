# JVL Roadmap

The plan for turning JVL from a working prototype into a full-fledged,
beautifully documented, openly usable project. Phases are ordered by leverage;
within a phase, items ship one at a time with tests and docs.

Legend: ✅ done · 🚧 in progress · ⬜ planned

---

## Phase 0 — Foundations ✅ (shipped in v0.1)

- ✅ Language surface: parties, facts, evidence, claims, rules, deontic nodes,
  constraints, exclusivity, queries.
- ✅ Epistemic lattice + standards of proof.
- ✅ Reference compiler: lexer → parser → forward-chaining evaluator → CLI.
- ✅ `check` / `assert` / `explain` / `discover` / `check-contradictions` /
  `constraints` / `simulate`.
- ✅ Docs set, 3 examples, 22-test suite, MIT licence, CI.

---

## Phase 1 — The program *is* the data layer 🚧

*Thesis: a JVL program can replace the JSON/graph layers — it already holds the
facts, relationships, and provenance, and it can compute. Make that real.*

- 🚧 **`jvl emit json`** — deterministic canonical JSON of the whole program
  (parties, atoms, statuses, provenance, rules). The interchange format falls
  out of the program, not a separate extractor.
- 🚧 **`jvl emit graph`** — export the case as a graph (nodes = atoms/parties,
  edges = supports/requires/refutes) in a standard format (JSON graph / DOT).
- ⬜ **`jvl emit` round-trips** — importing the JSON reproduces the same atoms.

## Phase 2 — Comparison & semantics 🚧

*Thesis (the user's core ask): given two legal documents as programs, tell me if
they mean the same thing, and if not, exactly what differs.*

- 🚧 **`jvl diff a.jvl b.jvl`** — structural + semantic diff: parties, facts
  (amounts/dates), rules, obligations, and resulting statuses added / removed /
  changed. Human-readable and machine-readable output.
- 🚧 **`jvl equiv a.jvl b.jvl`** — semantic-equivalence check: do the two
  programs entail the same conclusions over the same questions? Reports EQUIVALENT
  / DIFFERENT with the discriminating propositions.
- ⬜ **Normalisation** — a canonical form so cosmetic differences (ordering,
  ids, whitespace) never register as semantic change.
- ⬜ **`jvl assert-same doc.jvl against template.jvl`** — "is this contract the
  same as the reference template, and where does it deviate?"

## Phase 3 — Ask in natural language 🚧

*Thesis: convert the doc to a program once, then answer questions fast.*

- ✅ **AI helper on the website** — a serverless function drafts a JVL program
  from a plain-English scenario (LLM transforms; the engine decides). Key stays
  server-side; model configurable.
- ✅ **`jvl ask FILE "does B have to repay A?"`** — the LLM maps the English
  question to a JVL query; the engine computes the deterministic answer with its
  trace. (Needs `ANTHROPIC_API_KEY`; stdlib-only, no new deps.)
- ✅ **MCP server** (`mcp-server/`) — exposes check/assert/explain/discover/
  contradictions/constraints/emit/diff/equiv as MCP tools any agent can call.

## Phase 4 — Language depth 🚧

- ✅ **Default logic**: `normally ... except when ...` (Catala-style defeasible
  defaults) — in both the Python reference and the JS engine, with a worked
  example ([05](examples/05-limitation-default.jvl)).
- ⬜ Nested exceptions-to-exceptions (`except-to-exception`).
- ⬜ Duration/interval constraints (`within 3 years`), arithmetic expressions.
- ⬜ Burden-of-proof modelling per element and per party.
- ⬜ Provenance on inferences + `jvl check --audit` (atoms with no source path).
- ⬜ `jvl fmt` canonical formatter.

## Phase 5 — Tooling & ecosystem 🚧

- ✅ **JS build of the engine** (`site/jvl-engine.js`) powering an in-browser
  editor with live run — parity-tested against the Python reference.
- ✅ **VS Code / TextMate grammar** (`editor-support/vscode/`) for `.jvl` syntax
  highlighting.
- ⬜ Language server (LSP): hover-status, go-to-source, contradiction squiggles.
- ⬜ Compile-to-Prolog/ASP backend for hard queries.

## Phase 6 — Brand & website ✅

- ✅ **Logo / mark** (SVG) — scales of justice fused with a verification check.
- ✅ **Website** (`site/`) — landing, Learn (tour + syntax + convert-a-doc), Docs,
  Playground, Theory, and an interactive Editor.
- ✅ **Deploy on Vercel** (personal scope) — live at https://jvl-six.vercel.app;
  CI + deploy workflow in place.
- ✅ **In-browser editor** with live run and an AI helper.
- ✅ **Theory page** — Turing completeness, decidability, determinism, language design.

---

## Working principles

1. Every feature ships with a test and a docs update.
2. The core stays dependency-free and deterministic.
3. Nothing becomes a robot judge; JVL surfaces structure, humans judge.
4. If a change makes the language harder for an LLM to emit, it's suspect.

## Current focus

Phase 2 (`diff` / `equiv`) and Phase 6 (logo + website + Vercel) — in progress.
