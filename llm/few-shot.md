# Few-shot exemplars — document → JVL

Paste one or two of these into context to teach a model the mapping by example.
Each shows a short input passage and the JVL it should produce.

---

## Example 1 — a paragraph from a civil complaint

**Input document (`Complaint.pdf`, p.4 ¶9–11):**

> 9. On 10 March 2025, the plaintiff transferred ₹10,00,000 to the defendant, as
>    shown in the bank statement at Exhibit P-3.
> 10. The plaintiff says the sum was a loan repayable within one year. The
>    defendant contends it was an equity investment carrying no repayment.
> 11. In a WhatsApp message dated 12 March (Exhibit P-7), the defendant wrote
>    "I'll repay you next month."

**Expected JVL:**

```jvl
jurisdiction IN.Contract.v1

party plaintiff = Person "Plaintiff"
party defendant = Person "Defendant"

fact transfer : TransferOfValue {
    from: plaintiff  to: defendant  amount: INR 1_000_000  on: 2025-03-10
} from source(doc="Complaint", page=4, para=9, exhibit="P-3") status Established

claim c_loan   by plaintiff : "the sum was a loan repayable within a year" asserts Loan(transfer)
claim c_invest by defendant : "the sum was an equity investment"           asserts Investment(transfer)
exclusive { Loan(transfer) Investment(transfer) }

evidence repay_msg : Message { author: defendant  text: "I'll repay you next month." }
    from source(doc="Complaint", page=4, para=11, exhibit="P-7") supports RepaymentObligation(transfer)

rule loan_definition:
    Loan(t) requires TransferOfValue(t) RepaymentObligation(t)
rule repayment_obligation:
    RepaymentObligation(t) established_if AdmittedRepayment(t) or ContractRequiresRepayment(t)

assert Loan(transfer) under BalanceOfProbabilities
```

**Note what the model did right:** the transfer is `Established` (documented and
uncontested); the two characterisations are `claim`s, not facts, and marked
`exclusive`; the WhatsApp line is `evidence`, cited to its exhibit; the mental
"repayment obligation" is left to be *derived*, not asserted.

---

## Example 2 — a criminal charge with a missing element

**Input document (`FIR.pdf`, p.1 ¶3; `Exhibit_P3`; `WhatsApp_22`):**

> The accused induced the complainant to part with ₹25,00,000 on 2 November 2024
> by showing a fabricated returns projection (Exhibit P-3) and promising
> "guaranteed 40% returns" (WhatsApp_22). The complainant seeks conviction for
> cheating.

**Expected JVL:**

```jvl
jurisdiction IN.Penal.v1

party accused     = Person "Accused"
party complainant = Person "Complainant"

fact payment : DeliveryOfProperty {
    from: complainant  to: accused  amount: INR 2_500_000  on: 2024-11-02
} from source(doc="FIR", page=1, para=3) status Established

rule cheating:
    Cheating(p) requires
        Deception(p) DishonestInducement(p)
        DeliveryOfProperty(p) DishonestIntentionAtInception(p)

evidence brochure : Document { note: "fabricated returns projection" }
    from source(doc="Exhibit_P3", para=8) supports Deception(payment)
evidence promise : Message { author: accused  text: "guaranteed 40% returns" }
    from source(doc="WhatsApp_22", para=5) supports DishonestInducement(payment)

# No evidence establishes dishonest intention *at inception* — left UNKNOWN.

assert Cheating(payment) under BeyondReasonableDoubt
```

**Note what the model did *not* do:** it did not invent evidence for
`DishonestIntentionAtInception`. Running `jvl discover FIR.jvl "Cheating(payment)"`
then correctly reports that element as the missing piece, and the `assert` fails
the criminal standard — which is the honest result.

---

## Example 3 — objective defect in a contract

**Input:** an NDA capping penalties at ₹50,00,000; the complaint claims ₹80,00,000
in damages for a disclosure dated within the term.

```jvl
fact nda : Agreement { signed_on: 2025-01-15  expires_on: 2028-01-15  penalty_cap: INR 5_000_000 }
    from source(doc="NDA_executed", page=1, para=1) status Established
fact disclosure : Disclosure { by: Receiving  on: 2025-06-20  amount: INR 8_000_000 }
    from source(doc="Complaint", page=3, para=12) status Alleged

constraint damages_within_cap:  disclosure.amount <= nda.penalty_cap
constraint disclosure_in_term:  disclosure.on before nda.expires_on
```

`jvl constraints` reports `damages_within_cap: VIOLATED` — a purely objective
finding needing no legal judgement, and one prose review routinely misses.

---

## Example 4 — a defeasible limitation defence (default logic)

**Input:** a suit filed after the limitation period; but the debtor acknowledged
the debt in writing within the period, which resets the clock.

```jvl
party creditor = Person "Creditor"
party debtor   = Person "Debtor"

fact claim1 : DebtClaim { filed_on: 2025-05-01 }
    from source(doc="Plaint", page=1, para=2) status Established

evidence late : Record { note: "filed outside the 3-year window" }
    from source(doc="Plaint", page=1, para=5) supports FiledAfterLimitation(claim1)
evidence ack : Message { author: debtor  text: "I acknowledge the amount owed." }
    from source(doc="Email_2023", para=1) supports AcknowledgedWithinPeriod(claim1)

rule limitation_default:
    TimeBarred(c) normally
        FiledAfterLimitation(c)
    except when AcknowledgedWithinPeriod(c)

assert TimeBarred(claim1) under BalanceOfProbabilities
```

**Why this shape:** "normally time-barred, except when acknowledged" is a
*defeasible default*, not a plain conjunction. The model used `normally ...
except when ...` so the acknowledgement rebuts the default — `TimeBarred` comes
back `REFUTED`, and `jvl simulate --without ack` shows it flipping to time-barred.
