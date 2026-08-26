"""A tiny benchmark: how fast does JVL evaluate a large program?

Generates a program with N independent transactions (each a fact + evidence +
the loan rule), then times a full parse + evaluate. Run:

    python bench.py            # default N = 500
    python bench.py 2000
"""

from __future__ import annotations

import sys
import time

from jvl import Evaluator, parse


def make_program(n: int) -> str:
    lines = ["jurisdiction IN.Contract.v1",
             "rule loan_definition:",
             "    Loan(t) requires TransferOfValue(t) RepaymentObligation(t)"]
    for i in range(n):
        lines.append(
            f'fact t{i} : TransferOfValue {{ amount: INR 1000 }} '
            f'from source(doc="D{i}", page=1) status Established')
        lines.append(
            f'evidence e{i} : Message {{ text: "repay" }} '
            f'from source(doc="C{i}", para=1) supports RepaymentObligation(t{i})')
        lines.append(f"assert Loan(t{i}) under BalanceOfProbabilities")
    return "\n".join(lines)


def main() -> None:
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 500
    src = make_program(n)

    t0 = time.perf_counter()
    prog = parse(src)
    t1 = time.perf_counter()
    ev = Evaluator(prog).build()
    t2 = time.perf_counter()

    supported = sum(1 for k, s in ev.status.items()
                    if k[0] == "Loan" and s.name == "SUPPORTED")
    print(f"transactions:     {n}")
    print(f"atoms derived:    {len(ev.status)}")
    print(f"Loan == SUPPORTED: {supported}")
    print(f"parse:            {(t1 - t0) * 1000:.1f} ms")
    print(f"evaluate:         {(t2 - t1) * 1000:.1f} ms")
    print(f"total:            {(t2 - t0) * 1000:.1f} ms")


if __name__ == "__main__":
    main()
