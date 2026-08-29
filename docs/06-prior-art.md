# Prior Art — What LVL borrows, and where it differs

LVL is not being invented in a vacuum. Several excellent projects have attacked
neighbouring problems, and the right move is to study them closely and steal
freely. This survey records what each does well and precisely where LVL's goals
diverge. **Before inventing new syntax, read these.**

| Project | What it does | Closest to LVL on |
|---|---|---|
| **L4** (smucclaw) | DSL for legal rules/contracts; executable specs, tests, traces, REST/MCP | executable *rules* |
| **PROLEG / alt-proleg** | Prolog reasoning over allegations, evidence, exceptions, findings | *case/litigation* reasoning |
| **Catala** | Compiles legislation to executable code via default logic | *statute → code*, defaults |
| **Yuho** | Encodes statutes as typed ASTs; emits JSON, LegalRuleML, Alloy, ... | *Legal IR / compiler* |
| **DeonticBench** | LLM translates legal problems to Prolog, then executes them | the *LLM → formal → solver* pattern |
| **LegalRuleML** | OASIS standard representation for legal norms | *interchange IR* |
| **SMU `dsl`** | One source compiling to ASP, Prolog, Petri nets, DMN, Alloy, ... | *multi-target* architecture |
| **LegalGraphRAG** | Case graph + retrieval + LLM legal reasoning | the *graph* layer beneath LVL |

## The ones to study first

### L4 — the closest *language* project
A domain-specific language for law: one source produces executable rules, tests,
evaluation traces, REST APIs, JSON schemas, even MCP tools. Conceptually very
close to LVL's rule layer. **Where it stops:** L4 is about formalising *rules*.
It does not target the full "5,000-page case file → extract claims/evidence →
typed case IR → execute assertions" pipeline, and epistemic status + provenance
are not its centre of gravity.
<https://github.com/smucclaw/l4-ide>

### PROLEG — the closest *case-reasoning* project
Models rules, allegations, evidence, findings, exceptions, and plaintiff/
defendant burdens, producing a proof trace for why a party can or cannot
establish something. This is *litigation-shaped*, much closer to LVL's world than
Catala's statute-shaped view. **Where it differs:** truth is essentially boolean/
provable, and traceability to a source PDF is not a design concern.
<https://github.com/mixcode/alt-proleg>

### DeonticBench — one exact stage of the LVL pipeline
An LLM translates a legal problem into Prolog, and SWI-Prolog actually runs it.
That `LEGAL TEXT → LLM → PROLOG → SOLVER → ANSWER` loop *is* LVL's core insight,
demonstrated. **Where it differs:** it is a benchmark, not a case-file compiler
with provenance/graph/evidence infrastructure.
<https://github.com/guangyaodou/DeonticBench>

### Catala — statute → code, with real default logic
Designed to derive algorithms from legislation, with **default logic**
(*normally X, except if A, except-to-the-exception if B*) that mirrors how
statutes are actually written. LVL wants this; it is on the [roadmap](07-roadmap.md).
**Where it differs:** Catala expects a human to encode the legislation; it is not
built to ingest an arbitrary court file and emit an executable world model.
<https://github.com/CatalaLang/catala>

### Yuho — a Legal IR and compiler to study
Encodes statutes as typed ASTs and emits JSON, LegalRuleML, LaTeX, Mermaid,
Alloy, Akoma Ntoso. Its AST and type system are directly relevant to LVL's IR.
<https://github.com/gongahkia/yuho>

### LegalRuleML — consider it before inventing an IR
An OASIS standard for machine-readable legal norms, explicitly meant as an
intermediate layer between text and logic implementations. LVL could plausibly
emit a LegalRuleML-compatible representation rather than inventing everything.
<https://github.com/oasis-open/legalruleml-repo>

### SMU `dsl` — the multi-target philosophy
Experiments with one source representation compiling to ASP, Prolog, TypeScript,
Petri nets, DMN, BPMN, Catala, Alloy. Its answer to "JSON or graph or language or
solver?" is *"one source, many targets, chosen per operation"* — which is very
close to how LVL sees its own future backends.
<https://github.com/smucclaw/dsl>

## The gap LVL aims at

No existing project combines all three of:

1. **Epistemic status as a first-class type** (not boolean truth),
2. **Mandatory provenance** back to `doc/page/para/exhibit/speaker`, and
3. **An LLM-emittable surface syntax** designed for the case-file pipeline.

That specific combination — meant to turn *an arbitrary legal document* into a
*checkable program that stays honest about uncertainty and always cites the
record* — is the space LVL is trying to occupy.

## Pragmatic path

The sane build order borrows before it invents: prototype **case JSON/graph →
typed predicates → (optionally) Prolog first**, learning from PROLEG +
DeonticBench + L4, and only harden LVL's own syntax around the abstractions those
targets make ugly. See the [roadmap](07-roadmap.md).
