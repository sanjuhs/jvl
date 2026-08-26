# Examples

Runnable JVL programs, each exercising a different part of the language. From
`reference-impl/` (after `pip install -e .`), run the commands in each file's
header comment.

| File | Demonstrates |
|---|---|
| [`01-loan-vs-investment.jvl`](01-loan-vs-investment.jvl) | Competing characterisations, evidence raising a proposition to `Supported`, and a `simulate` counterfactual that collapses the claim. |
| [`02-nda-contract.jvl`](02-nda-contract.jvl) | The deontic layer (`obligation` / `prohibition`) and objective `constraint` checking — the compiler catches damages exceeding the contractual cap. |
| [`03-cheating-s420.jvl`](03-cheating-s420.jvl) | A criminal offence as a conjunction of elements, `discover` pinpointing the unproven mental element, failure under `BeyondReasonableDoubt`, and a contradiction from conflicting evidence. |
| [`04-service-agreement-v1/v2.jvl`](04-service-agreement-v1.jvl) | A versioned contract pair for `diff` and `equiv` — "do these two contracts mean the same thing?" |
| [`05-limitation-default.jvl`](05-limitation-default.jvl) | Defeasible **default logic** — `normally time-barred … except when acknowledged`; the exception rebuts the default, and `simulate --without ack` restores it. |

## Try it in 30 seconds

```bash
cd reference-impl && pip install -e .
jvl assert   ../examples/01-loan-vs-investment.jvl
jvl discover ../examples/03-cheating-s420.jvl "Cheating(payment)"
jvl check-contradictions ../examples/03-cheating-s420.jvl
jvl constraints ../examples/02-nda-contract.jvl
```

> Every example uses invented facts and illustrative (not real) legal rules.
> They demonstrate the language, not the law of any jurisdiction.
