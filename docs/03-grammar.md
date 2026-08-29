# Grammar reference

The authoritative grammar is [`spec/grammar.ebnf`](../spec/grammar.ebnf). This
page is the friendly companion to it.

## Lexical rules

- **Whitespace and newlines are insignificant.** They separate tokens; nothing
  more. Indent however reads best.
- **Comments:** `#` or `//` to end of line.
- **Identifiers:** `letter (letter | digit | _)*`, and may be **dotted**
  (`IN.Contract.v1`, `nda.penalty_cap`).
- **Numbers:** digits with optional `_` separators and decimal point
  (`1_000_000`, `40.5`). Underscores are stripped.
- **Money:** a currency code followed by a number (`INR 1_000_000`).
- **Dates:** ISO `YYYY-MM-DD` (`2025-03-10`).
- **Strings:** double-quoted, with `\` escapes.

## Statement quick reference

```lvl
jurisdiction IN.Contract.v1

party ID = Type "label"

fact ID : Type { field: value, ... } from source(doc="...", page=N, para=N) status Kw

evidence ID : Type { ... } from source(...) supports Pred(args)
evidence ID : Type { ... } from source(...) refutes  Pred(args)

claim ID by Party : "text" asserts Pred(args)

rule ID: Head(t) requires        BodyA(t) BodyB(t)
rule ID: Head(t) established_if   BranchA(t) or BranchB(t)
rule ID: Head(t) normally BodyA(t) except when ExceptionA(t)   # defeasible default

obligation  ID { bearer: P, to: Q, that: Pred(P), by: DATE, on_breach: Pred(P) }
permission  ID { ... }
prohibition ID { ... }

constraint ID: value OP value          # OP: <= >= < > == !=  before after
constraint ID: DATE within N days after DATE   # duration: of | before | after
                                               #  (units: days weeks months years)

exclusive { PredA(t) PredB(t) }

assert  Pred(args) under Standard for Party
prove   Pred(args) ...                 # synonym for assert
refute  Pred(args)
explain Pred(args)
discover Pred(args)
```

## Predicates

A predicate is `Name(arg, arg, ...)`. Arguments are entity identifiers,
variables, or literals. **Convention:** predicate names are `UpperCamelCase`
(`RepaymentObligation`), variables are lowercase (`t`), entities are `snake_case`
or short (`transfer_17`, `A`). The compiler treats any lowercase, undeclared
argument inside a rule as a variable.

## Fields with predicate values

Inside a `{ ... }` record, a value may itself be a predicate — this is how
`obligation` carries `that:` and `on_breach:`:

```lvl
obligation notify { bearer: B, to: A, that: NotifyOnRequest(B), by: 2025-07-01 }
```

## What is intentionally *not* in the grammar (yet)

Arithmetic expressions, quantifiers, nested exceptions-to-exceptions, and
temporal-interval operators. (First-class `normally ... except when ...` defaults
*are* supported — see above.) See the [roadmap](../ROADMAP.md). Keeping the
surface tiny is what makes it reliably machine-writable.
