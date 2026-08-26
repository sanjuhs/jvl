"""JVL — Jhana Verifiable Law: a language for compiling legal documents into
statically-checkable programs.

Public API::

    from jvl import parse, Evaluator
    prog = parse(open("case.jvl").read())
    ev = Evaluator(prog).build()
    ev.run_assert(target, standard)
"""

from .evaluator import Evaluator
from .lattice import Standard, Status, Verdict
from .parser import parse

__version__ = "0.1.0"
__all__ = ["parse", "Evaluator", "Status", "Standard", "Verdict", "__version__"]
