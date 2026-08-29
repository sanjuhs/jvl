"""LVL — Legal Verifiable Language: a language for compiling legal documents into
statically-checkable programs.

Public API::

    from lvl import parse, Evaluator
    prog = parse(open("case.lvl").read())
    ev = Evaluator(prog).build()
    ev.run_assert(target, standard)
"""

from . import compare, serialize
from .evaluator import Evaluator
from .lattice import Standard, Status, Verdict
from .parser import parse

__version__ = "0.2.0"
__all__ = [
    "parse", "Evaluator", "Status", "Standard", "Verdict",
    "compare", "serialize", "__version__",
]
