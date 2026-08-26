# jvl — the JVL reference compiler

The reference implementation of **JVL (Jhana Verifiable Law)**: a language for
compiling legal documents into statically-checkable programs. Facts carry
provenance; propositions carry an epistemic status on a truth lattice; legal
arguments type-check.

Zero runtime dependencies (Python 3.10+).

```bash
pip install -e .
jvl check    ../examples/01-loan-vs-investment.jvl
jvl assert   ../examples/01-loan-vs-investment.jvl
jvl discover ../examples/03-cheating-s420.jvl "Cheating(payment)"
jvl equiv    ../examples/04-service-agreement-v1.jvl ../examples/04-service-agreement-v2.jvl
```

Commands: `check`, `assert`/`prove`, `refute`, `explain`, `discover`,
`check-contradictions`, `constraints`, `simulate`, `emit`, `diff`, `equiv`,
`ask`.

Full project, docs, and website: <https://github.com/sanjuhs/jvl> ·
<https://jvl-six.vercel.app>

Library API:

```python
from jvl import parse, Evaluator, Standard
ev = Evaluator(parse(open("case.jvl").read())).build()
```

MIT licensed.
