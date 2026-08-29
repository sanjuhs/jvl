# Extraction Guide — Reading a document into LVL

This is the *method*: how to turn prose into an LVL program, one pass at a time.
It is written for a language model, but a human learning the language will find
it the fastest way in too.

## The five-pass method

Do not try to write the whole program at once. Make five cheap passes over the
document, each producing one kind of node.

### Pass 1 — Parties (the nouns)
Find every person and organisation that acts or is acted upon. Emit a `party` for
each, with a short id you will reuse.

```lvl
party A = Person "Anil Kumar"
party B = Person "Beena Rao"
```

### Pass 2 — Facts (what happened), with sources and status
Find events and states the document treats as *having occurred*. For each, ask
the two LVL questions: **where is this in the document?** (provenance) and **how
firmly is it accepted?** (status).

```lvl
fact transfer_17 : TransferOfValue {
    from: A  to: B  amount: INR 1_000_000  on: 2025-03-10
} from source(doc="BankStatement_3", page=2, para=4) status Established
```

Status cheat-sheet:

| The document says... | Use |
|---|---|
| agreed / admitted / conceded | `Admitted` |
| found proven / established | `Established` |
| alleged / claimed / it is said | `Alleged` |
| disputed / contested | `Disputed` |
| disproven / rebutted | `Refuted` |

### Pass 3 — Claims and evidence (the contest)
Separate *contentions* from *proof*:

- A party's assertion of a legal characterisation → `claim`.
- A concrete document/message/testimony bearing on a proposition → `evidence`
  with `supports` or `refutes`.

```lvl
claim c_loan by A : "the transfer was a loan" asserts Loan(transfer_17)

evidence w17 : Message { author: B  text: "I'll repay you next month." }
    from source(doc="WhatsApp_17", para=21) supports RepaymentObligation(transfer_17)
```

If two characterisations are incompatible, record it:

```lvl
exclusive { Loan(transfer_17) Investment(transfer_17) }
```

### Pass 4 — The law (rules)
Encode the relevant legal tests as `rule`s. Most reduce to conjunction or
disjunction:

```lvl
rule cheating:
    Cheating(p) requires
        Deception(p) DishonestInducement(p)
        DeliveryOfProperty(p) DishonestIntentionAtInception(p)
```

**Do not fabricate elements.** If the record does not support
`DishonestIntentionAtInception`, leave it unstated. Its `UNKNOWN` status is the
truthful answer, and `discover` will surface it as the gap.

For **"normally X, except Y"** statute language — limitation periods,
presumptions, carve-outs — use a defeasible default rather than a conjunction:

```lvl
rule limitation_default:
    TimeBarred(c) normally FiledAfterLimitation(c)
    except when AcknowledgedWithinPeriod(c)
```

### Pass 5 — Constraints and questions
Turn objective relations into `constraint`s, and the ultimate issues into
`assert`s under the right standard:

```lvl
constraint damages_within_cap: disclosure_event.amount <= nda.penalty_cap
constraint delivered_in_window: delivery.on within 30 days after contract.due
assert Cheating(payment) under BeyondReasonableDoubt
```

Deadlines and grace windows use the duration form (`within N days/weeks/months/
years of/before/after`), so time limits are checked, not just asserted.

## Judgement calls, and how to make them safely

- **Objective vs. non-objective.** Amounts, dates, durations, arithmetic → always
  encode as facts/constraints; they are checkable. Open-textured concepts
  ("reasonable", "dishonest") → encode the *element* as a predicate, but only
  mark it `Supported` when the document actually supplies evidence for it.
- **When unsure of a status, go lower.** Prefer `Alleged` over `Established`,
  `claim` over `fact`. Under-claiming is safe; over-claiming manufactures false
  certainty.
- **When the law is genuinely open**, stop. Encode the structure and leave the
  contested proposition `UNKNOWN`. LVL is built to hand exactly that question to a
  human, not to guess it.

## After extraction: the compile loop

1. Run `lvl check case.lvl`. Read every diagnostic.
2. Fix errors (undeclared party, bad standard); address warnings (missing
   source).
3. Run `lvl assert` / `lvl explain` and read the trace.
4. Present the program **and** the trace to the human — never a bare conclusion.

See [`few-shot.md`](few-shot.md) for full document → LVL examples.
