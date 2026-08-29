# lvl — the LVL reference compiler

The reference implementation of **LVL (Legal Verifiable Language)**: a language for
compiling legal documents into statically-checkable programs. Facts carry
provenance; propositions carry an epistemic status on a truth lattice; legal
arguments type-check.

Zero runtime dependencies (Python 3.10+).

```bash
pip install -e .
lvl check    ../examples/01-loan-vs-investment.lvl
lvl assert   ../examples/01-loan-vs-investment.lvl
lvl discover ../examples/03-cheating-s420.lvl "Cheating(payment)"
lvl equiv    ../examples/04-service-agreement-v1.lvl ../examples/04-service-agreement-v2.lvl
```

Commands: `check`, `assert`/`prove`, `refute`, `explain`, `discover`,
`check-contradictions`, `constraints`, `simulate`, `emit`, `diff`, `equiv`,
`ask`.

Full project, docs, and website: <https://github.com/sanjuhs/lvl> ·
<https://lvl-lang.vercel.app>

Library API:

```python
from lvl import parse, Evaluator, Standard
ev = Evaluator(parse(open("case.lvl").read())).build()
```

MIT licensed.
