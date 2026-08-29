# The Provenance Model

Provenance is the feature LVL refuses to treat as optional. A formal proof is
only as trustworthy as the facts it rests on, and in an LLM-driven pipeline the
facts are extracted by a model that can hallucinate. **A conclusion you cannot
trace back to the record is worse than no conclusion — it is a confident error.**

## The `source(...)` attachment

Every `fact` and every `evidence` node may carry a source:

```lvl
fact transfer_17 : TransferOfValue { ... }
    from source(doc="BankStatement_3", page=2, para=4, exhibit="P-3", speaker="B")
    status Established
```

| Key | Meaning |
|---|---|
| `doc` | the source document identifier |
| `page` | page number within it |
| `para` | paragraph number |
| `exhibit` | exhibit marking (e.g. `P-17`, `D-2`) |
| `speaker` | who said it, for testimony and messages |

All keys are optional individually, but **omitting `source(...)` entirely earns a
compiler warning** (`lvl check`). The intent is social as much as technical: a
LVL program with clean provenance is one a reviewer can audit line by line
against the actual file.

## Provenance flows into every trace

Provenance is not stored and forgotten — it appears at every rung of a
derivation. When you `explain` or `assert`, each leaf of the tree carries its
source:

```
RepaymentObligation(transfer_17) .......... SUPPORTED
  └─ supporting evidence (w17)  →  WhatsApp_17 ¶21
```

So the answer to "why does this hold?" always bottoms out at "because of *this
line in this document*," never at an unexplained assertion.

## The epistemic chain provenance preserves

Pure JSON extraction flattens the ladder from raw quote to legal conclusion. LVL
keeps every rung addressable:

```
OBSERVATION   raw text in the file
   ↓ extracted as
CLAIM         a party's contention                 (claim ... by ...)
   ↓ supported by
EVIDENCE      a document/message/testimony          (evidence ... supports ...)
   ↓ permits
INFERENCE     what the evidence lets you conclude   (a rule)
   ↓ relevant to
LEGAL PROPOSITION   an element of law               (a predicate)
   ↓ contributes to
LEGAL CONCLUSION    the ultimate question           (assert ...)
```

Each layer has a distinct node kind, and each retains its link downward. That is
what lets a human stand at the top — "the transaction was a loan" — and walk all
the way down to "because of ¶21 of WhatsApp_17."

## Roadmap: provenance as a first-class value

Today provenance is metadata on facts and evidence. Planned:

- **Provenance on inferences**, so a derived proposition records not just its
  rule but the specific source spans that fed each element.
- **A `--audit` mode** that lists every atom with no path to any source — the
  "unsupported by the record" report.
- **Character-offset spans** (`doc#L473-L488`) for exact highlighting back in the
  original PDF or text.
