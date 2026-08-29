# Contributing to LVL

LVL is early and experimental, which means your contribution can still shape the
language itself. Thank you for being here.

## Good first contributions

- **Worked examples** (`examples/*.lvl`). A realistic-but-anonymised case,
  encoded end to end, is the single most valuable thing you can add. It stresses
  the language and teaches the next person.
- **Jurisdiction libraries** (`spec/stdlib/<jurisdiction>/*.lvl`). Encode a
  well-known offence or contract doctrine as LVL rules, citing the real statute
  in comments. Keep it clearly marked as illustrative unless it is rigorously
  sourced.
- **Parser hardening.** Feed the reference implementation weird-but-valid inputs
  and fix what breaks. Add a failing test first.
- **Documentation.** If something in `docs/` confused you, a PR that unconfuses
  the next reader is welcome.

## Development setup

```bash
cd reference-impl
pip install -e ".[dev]"
pytest -q
```

The reference implementation has **no third-party runtime dependencies** — please
keep it that way. `pytest` is the only dev dependency.

## Code conventions

- Python 3.10+, standard library only for the core.
- Prefer clarity over cleverness — this compiler is meant to be *read* by people
  learning how LVL works. Comment the *why*, not the *what*.
- Every behavioural change needs a test in `reference-impl/tests/`.
- If you change the language surface, update **all** of: `spec/grammar.ebnf`,
  `docs/03-grammar.md`, the tour, and at least one example.

## Proposing language changes

Open an issue describing the construct, a motivating legal example, and how it
evaluates (what status does it produce, and why?). Language changes are held to a
high bar: the syntax must stay deterministic to parse and realistic for an LLM to
emit. If a proposal makes the language harder for a model to write correctly,
that is a strong argument against it.

## Scope and spirit

LVL makes legal reasoning explicit and checkable. It is **not** a robot judge and
**not** legal advice. Contributions that push it toward auto-deciding cases, or
that fake precision where the law is genuinely open, are out of scope. See the
[manifesto](docs/00-manifesto.md).

## Licence

By contributing you agree your contributions are licensed under the project's
[MIT licence](LICENSE).
