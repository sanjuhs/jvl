# Semantics — How JVL decides what holds

This is the precise account of what a JVL program *means*. The reference
implementation (`reference-impl/jvl/lattice.py` and `evaluator.py`) is the
executable version of everything below.

## 1. The epistemic lattice

Every proposition (atom) has a **status**:

```
REFUTED  <  UNSUPPORTED  <  UNKNOWN  <  DISPUTED  <  SUPPORTED  <  PROVEN
  0            1             2           3            4            5
```

`ESTABLISHED` shares the top rank (5) with `PROVEN`; the difference is only in
the label — `ESTABLISHED` marks a directly-asserted primary fact, `PROVEN` marks
something a rule concluded. They behave identically against a standard of proof.

Reading the ordering: it measures **how much the record supports the proposition
being true**. `REFUTED` is worst (evidence says false); `UNKNOWN` is the neutral
default (no information); `DISPUTED` sits above unknown because there *is*
evidence, but it points both ways; `SUPPORTED`/`PROVEN` are genuine support.

## 2. Combining evidence on one proposition — `combine`

A single atom may receive many contributions (a fact, several pieces of
evidence, a claim, and the output of rules). They aggregate like this:

- If there is a contribution *for* it (rank ≥ `SUPPORTED`) **and** one *against*
  it (`REFUTED`) → **`DISPUTED`**. Contradiction is surfaced, never averaged
  away.
- Otherwise the result is the **strongest** contribution (highest rank).
- No contributions at all → **`UNKNOWN`**.

This is why two conflicting witnesses produce `DISPUTED` rather than a false
resolution — the system's job is to *show* you the conflict.

## 3. Combining elements of a rule — `meet` and `join`

- **`requires` (conjunction) uses `meet` = the minimum rank.** An argument is
  only as strong as its weakest element. `Loan requires TransferOfValue ∧
  RepaymentObligation`: if the obligation is only `Supported`, the loan is at
  best `Supported`, even if the transfer is `Established`.
- **`established_if ... or ... (disjunction) uses `join` = the maximum rank.**
  The head is as strong as its strongest satisfied branch.

`meet` and `join` make the status lattice a genuine lattice, which is what lets
evaluation reach a stable answer.

## 4. Standards of proof — when does a status *count as holding*?

A status is just a position on the lattice. Whether it is "good enough" depends
on the **standard** the question is asked under:

| Standard | Minimum status to hold |
|---|---|
| `BalanceOfProbabilities` | `SUPPORTED` |
| `ClearAndConvincing` | `SUPPORTED` (stricter in doctrine; see note) |
| `BeyondReasonableDoubt` | `PROVEN` |

Two hard rules:

- **`DISPUTED` never meets any standard.** A live conflict must be resolved
  before anything built on it can be certified.
- A civil claim clears at `SUPPORTED`; a criminal charge needs `PROVEN`. This is
  why the same evidence can win a civil case and lose a criminal one — and JVL
  shows exactly that in [example 03](../examples/03-cheating-s420.jvl).

> **Honest simplification.** Real standards of proof are not a single scalar, and
> `ClearAndConvincing` genuinely sits between the other two. v0.1 collapses it to
> the same threshold as balance-of-probabilities and marks the gap as future
> work. We would rather ship a documented approximation than a false precision.

## 5. Evaluation — a forward-chaining fixpoint

The evaluator (`evaluator.py`):

1. Reads `fact` / `evidence` / `claim` nodes into **base contributions** on
   atoms.
2. Repeatedly applies every `rule` to every binding of its variables over the
   declared entities, recomputing head statuses from the previous pass, until
   nothing changes (a fixpoint) or a safety cap is hit.
3. A rule only "fires" for a binding when at least one body atom is already
   non-`UNKNOWN` — so the evaluator never manufactures propositions out of thin
   air.

The algorithm is deliberately naive: legal programs are small, and a readable
evaluator is worth more than a fast one. Determinism falls out for free — same
program, same fixpoint, same trace, every run (§8).

## 6. Contradiction detection

Two independent mechanisms, both surfaced by `jvl check-contradictions`:

- **Evidential:** any atom that resolves to `DISPUTED`.
- **Declared:** an `exclusive { ... }` set with two or more members at
  `SUPPORTED` or above.

Note what this enables: you can load a large program and ask *"is this set of
clauses even internally consistent?"* — a question natural language cannot be
asked at all.

## 7. Objective constraints

`constraint` relations are evaluated directly, outside the epistemic lattice,
because they need no legal judgement:

- Money compares only within the same currency (a mismatch is reported, not
  silently coerced).
- ISO dates compare correctly as strings; `before` / `after` are provided as
  readable aliases.
- `id.field` dereferences a field on a declared fact.

A violated constraint (e.g. claimed damages above a contractual cap) is a hard,
non-arguable defect.

## 8. Determinism, and where it stops

JVL is deterministic by construction: no ordering-dependence (the fixpoint is
order-free), no randomness, no hidden state. The *same program always yields the
same answer and the same explanation*. This is the point — we are trying to make
the mechanical part of law actually mechanical.

Determinism stops exactly where the law stops being determinate: at genuine
balancing tests, discretion, and open-textured standards. JVL's design response
is not to fake a number there, but to leave the proposition `UNKNOWN` or
`DISPUTED` and let `discover` hand the precise open question to a human. The
language draws a bright line between *"the computer resolved this"* and *"a human
must"*, and never blurs it.

## 9. What the type system checks statically (`jvl check`)

- Missing provenance on `fact` / `evidence` → **warning**.
- A `claim by` an undeclared party → **error**.
- An unknown standard of proof in a query → **error**.
- A predicate used with inconsistent arity across the program → **warning**.

These run before any evaluation — the "does this legal argument type-check?"
pass.
