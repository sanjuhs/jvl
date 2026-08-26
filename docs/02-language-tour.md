# The JVL Language Tour

A guided walk through the whole language in one sitting. If you can read a little
code and a little law, you can finish this in twenty minutes and write your own
programs afterward. Nothing here is more complex than it needs to be — that is a
design goal, not an accident.

> **Mental model.** A JVL program is a small world. You *declare who exists*,
> *state what happened* (with a source and a confidence), *write down the rules
> of law*, and then *ask questions*. The compiler answers, and shows its work.

---

## 0. Hello, world (of a dispute)

Here is a complete, runnable program. We will build it up piece by piece.

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

claim c_loan by A : "the transfer was a loan" asserts Loan(transfer_17)

evidence w17 : Message {
    author: B
    text:   "I'll repay you next month."
} from source(doc="WhatsApp_17", para=21) supports RepaymentObligation(transfer_17)

rule loan_definition:
    Loan(t) requires TransferOfValue(t) RepaymentObligation(t)

rule repayment_obligation:
    RepaymentObligation(t) established_if AdmittedRepayment(t) or ContractRequiresRepayment(t)

assert Loan(transfer_17) under BalanceOfProbabilities
```

Run it:

```bash
jvl assert examples/01-loan-vs-investment.jvl
```

Now let's understand every line.

---

## 1. `jurisdiction` — which body of law is in force

```jvl
jurisdiction IN.Contract.v1
```

A dotted name identifying the rule library this program reasons under. It is
metadata today; in future it will select which `spec/stdlib/` library loads.

## 2. `party` — declare who exists

```jvl
party A = Person "Anil Kumar"
party B = Person "Beena Rao"
```

`A` is the **identifier** you use everywhere else; `"Anil Kumar"` is the display
label. Types you'll see: `Person`, `Org`. Parties are the nouns of your world.

## 3. `fact` — state what happened, with a source and a status

```jvl
fact transfer_17 : TransferOfValue {
    from:   A
    to:     B
    amount: INR 1_000_000
    on:     2025-03-10
} from source(doc="BankStatement_3", page=2, para=4) status Established
```

Read it as: *there is a fact called `transfer_17`, of type `TransferOfValue`,
with these fields; it comes from page 2 ¶4 of BankStatement_3; and its status is
`Established`.*

- The `{ ... }` block holds **fields**. Values can be references (`A`), money
  (`INR 1_000_000` — underscores are ignored), dates (`2025-03-10`), numbers, or
  strings.
- `from source(...)` is the **provenance**. Keys: `doc`, `page`, `para`,
  `exhibit`, `speaker`. Omit it and `jvl check` will warn you — a fact with no
  source is not trustworthy.
- `status` is how well the fact is accepted. Common values: `Established`,
  `Admitted`, `Alleged`, `Disputed`, `Refuted`. This is your first taste of JVL
  never treating truth as a plain boolean.

Declaring `fact transfer_17 : TransferOfValue { ... }` also asserts the
proposition **`TransferOfValue(transfer_17)`** at the given status. That is the
bridge from a data record to a logical atom.

## 4. `claim` — who asserts what

```jvl
claim c_loan by A : "the transfer was a loan" asserts Loan(transfer_17)
```

A claim is a *party's contention*, not a fact. On its own it contributes only
`Unsupported` weight — someone said it, nothing yet backs it. Claims are how you
capture the adversarial structure: two parties, two incompatible stories.

## 5. `evidence` — things that bear on a proposition

```jvl
evidence w17 : Message {
    author: B
    text:   "I'll repay you next month."
} from source(doc="WhatsApp_17", para=21) supports RepaymentObligation(transfer_17)
```

Evidence is like a fact but it points at a proposition: `supports` raises that
proposition toward `Supported`; `refutes` pushes it toward `Refuted`. When a
proposition has both, JVL marks it `Disputed` and flags a contradiction (§10).

## 6. `rule` — the law itself

Two shapes cover most of legal logic:

```jvl
# Conjunction: ALL elements required (a "meet" — as strong as the weakest part)
rule loan_definition:
    Loan(t) requires
        TransferOfValue(t)
        RepaymentObligation(t)

# Disjunction: ANY branch suffices (a "join" — as strong as the strongest part)
rule repayment_obligation:
    RepaymentObligation(t) established_if
        AdmittedRepayment(t)
        or ContractRequiresRepayment(t)
```

- `t` is a **variable** (lowercase, undeclared). It binds to concrete entities
  like `transfer_17` when the rule runs.
- `requires` combines its body with **AND**; `established_if` with **OR**. That
  is the whole of the propositional logic, and it is enough for a surprising
  amount of law.

## 7. `assert` — ask a question

```jvl
assert Loan(transfer_17) under BalanceOfProbabilities
```

This asks: *does `Loan(transfer_17)` hold, to the civil standard?* The answer is
not yes/no — it is a **status plus a derivation trace**:

```
  Loan(transfer_17) ............................. SUPPORTED
    └─ requires: TransferOfValue(transfer_17) ∧ RepaymentObligation(transfer_17)
      TransferOfValue(transfer_17) .............. ESTABLISHED
        └─ Established fact (transfer_17)  →  BankStatement_3 p.2 ¶4
      RepaymentObligation(transfer_17) .......... SUPPORTED
        └─ supporting evidence (w17)  →  WhatsApp_17 ¶21

  RESULT: SUPPORTED  ✓ (meets BalanceOfProbabilities)
```

`prove` is a synonym for `assert`. `refute X` asks whether X is disproven.

---

## 8. Writing assertions over *someone else's* program

You do not have to author a whole case to query one. Assertions are the primary
way humans interrogate an existing JVL program, and there are two ways to write
them:

**In the file** — add a line and re-run:

```jvl
assert BreachOfNDA(disclosure_event) under BeyondReasonableDoubt
```

**From the command line** — no editing required:

```bash
jvl explain  case.jvl "RepaymentObligation(transfer_17)"   # full trace
jvl discover case.jvl "Cheating(payment)"                   # what's missing?
```

`explain` gives the whole derivation tree for any proposition. `discover` is the
one lawyers fall in love with: it tells you *which elements of a claim are not
yet established*, so you know exactly what evidence you still need:

```
⚖  discover  what is missing for Cheating(payment)
  ✗ DishonestIntentionAtInception(payment) — UNKNOWN
```

## 9. `constraint` — the objective, purely-checkable layer

Some things need no legal judgement at all — they are arithmetic and calendars:

```jvl
constraint damages_within_cap:  disclosure_event.amount <= nda.penalty_cap
constraint disclosure_in_term:  disclosure_event.on before nda.expires_on
```

`id.field` reads a field off a declared fact. Operators: `<= >= < > == !=` for
money and numbers, `before / after` for dates. Run them:

```bash
jvl constraints case.jvl
#   ✗ damages_within_cap: VIOLATED     ← claimed damages exceed the contract cap
#   ✓ disclosure_in_term: holds
```

This is the "deterministic core" of the language: given the numbers, the answer
is not arguable.

## 10. Finding contradictions

Two ways JVL surfaces conflict:

1. **Evidence both ways.** If one piece of evidence `supports` and another
   `refutes` the same proposition, it becomes `Disputed`.
2. **Declared mutual exclusion.** State that two propositions cannot co-exist:

```jvl
exclusive { Loan(transfer_17) Investment(transfer_17) }
```

If both ever become `Supported`, the checker reports it:

```bash
jvl check-contradictions case.jvl
#   ⚠ MUTUAL EXCLUSION VIOLATED: Loan(...), Investment(...) cannot all hold
```

## 11. `obligation` / `permission` / `prohibition` — the deontic layer

Contracts are mostly *duties*, so JVL has first-class deontic nodes:

```jvl
obligation notify {
    bearer: Receiving
    to:     Disclosing
    that:   NotifyOnRequest(Receiving)
    by:     2025-07-01
}

prohibition keep_secret {
    bearer:    Receiving
    that:      Discloses(Receiving)
    on_breach: liable(Receiving, damages)
}
```

`that:` is the propositional content; `by:` a deadline; `on_breach:` the
consequence if it fails. These make the *structure* of a contract explicit and
checkable.

## 12. Counterfactuals — `simulate`

Ask what the case looks like if a piece of it vanishes:

```bash
jvl simulate case.jvl --without w17
#   Loan(transfer_17): UNKNOWN   ← changed from SUPPORTED
```

Remove the WhatsApp message and the loan claim collapses. This is how you weigh
what a single exhibit is actually carrying.

---

## The whole language, on one page

| Keyword | Purpose |
|---|---|
| `jurisdiction` | which rule library is in force |
| `party` | declare a person/org |
| `fact` | state something that happened (+ source + status) |
| `evidence` | something that `supports` / `refutes` a proposition |
| `claim` | a party's contention |
| `rule ... requires` | conjunction (AND) of elements |
| `rule ... established_if` | disjunction (OR) of branches |
| `obligation` / `permission` / `prohibition` | deontic duties |
| `constraint` | objective money/date/number comparison |
| `exclusive` | propositions that cannot co-exist |
| `assert` / `prove` / `refute` | ask whether something holds |
| `explain` / `discover` | trace it / find what's missing |

That is the entire language. Everything else is vocabulary you define in rules.

**Next:** the [semantics](04-semantics.md) (how statuses combine, exactly), the
[provenance model](05-provenance.md), or just open [`examples/`](../examples/)
and start editing.
