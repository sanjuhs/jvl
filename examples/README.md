# Examples

Runnable LVL programs, each exercising a different part of the language. From
`reference-impl/` (after `pip install -e .`), run the commands in each file's
header comment.

| File | Demonstrates |
|---|---|
| [`01-loan-vs-investment.lvl`](01-loan-vs-investment.lvl) | Competing characterisations, evidence raising a proposition to `Supported`, and a `simulate` counterfactual that collapses the claim. |
| [`02-nda-contract.lvl`](02-nda-contract.lvl) | The deontic layer (`obligation` / `prohibition`) and objective `constraint` checking — the compiler catches damages exceeding the contractual cap. |
| [`03-cheating-s420.lvl`](03-cheating-s420.lvl) | A criminal offence as a conjunction of elements, `discover` pinpointing the unproven mental element, failure under `BeyondReasonableDoubt`, and a contradiction from conflicting evidence. |
| [`04-service-agreement-v1/v2.lvl`](04-service-agreement-v1.lvl) | A versioned contract pair for `diff` and `equiv` — "do these two contracts mean the same thing?" |
| [`05-limitation-default.lvl`](05-limitation-default.lvl) | Defeasible **default logic** — `normally time-barred … except when acknowledged`; the exception rebuts the default, and `simulate --without ack` restores it. |
| [`06-capstone-commercial-dispute.lvl`](06-capstone-commercial-dispute.lvl) | **The whole language in one file** — facts, evidence, claims, a disjunction rule, a defeasible default, deontic obligations, constraints, and exclusivity. Shows a disjunction succeeding on its strong branch while the other branch is `DISPUTED`. |

## Try it in 30 seconds

```bash
cd reference-impl && pip install -e .
lvl assert   ../examples/01-loan-vs-investment.lvl
lvl discover ../examples/03-cheating-s420.lvl "Cheating(payment)"
lvl check-contradictions ../examples/03-cheating-s420.lvl
lvl constraints ../examples/02-nda-contract.lvl
```

> Every example uses invented facts and illustrative (not real) legal rules.
> They demonstrate the language, not the law of any jurisdiction.
