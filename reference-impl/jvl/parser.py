"""Recursive-descent parser: tokens -> AST.

The grammar is small enough to parse by hand, and doing so keeps error messages
legible for the two audiences that matter: a lawyer reading a mistake, and a
language model being told its output didn't parse. The authoritative grammar
lives in ``spec/grammar.ebnf``; this file is the implementation of it.
"""

from __future__ import annotations

from . import ast
from .lexer import Token, tokenize

# Words that begin a top-level statement. Used to know where a rule body ends.
_STMT_KEYWORDS = {
    "jurisdiction", "party", "fact", "evidence", "claim", "rule",
    "obligation", "permission", "prohibition", "constraint", "exclusive",
    "assert", "prove", "refute", "explain", "discover",
}

_CURRENCIES = {"INR", "USD", "EUR", "GBP", "JPY", "AUD", "CAD", "SGD", "CNY", "CHF"}


class ParseError(SyntaxError):
    pass


class Parser:
    def __init__(self, tokens: list[Token]):
        self.toks = tokens
        self.i = 0

    # --- cursor helpers ---------------------------------------------------
    def peek(self, k: int = 0) -> Token:
        j = min(self.i + k, len(self.toks) - 1)
        return self.toks[j]

    def next(self) -> Token:
        t = self.toks[self.i]
        if self.i < len(self.toks) - 1:
            self.i += 1
        return t

    def at(self, kind: str, value: str | None = None) -> bool:
        t = self.peek()
        return t.kind == kind and (value is None or t.value == value)

    def at_keyword(self, *words: str) -> bool:
        t = self.peek()
        return t.kind == "IDENT" and t.value in words

    def expect(self, kind: str, value: str | None = None) -> Token:
        t = self.peek()
        if t.kind != kind or (value is not None and t.value != value):
            want = f"{kind} {value!r}" if value else kind
            raise ParseError(
                f"line {t.line}, col {t.col}: expected {want}, got {t.kind} {t.value!r}"
            )
        return self.next()

    def _span(self) -> ast.Span:
        t = self.peek()
        return ast.Span(t.line, t.col)

    # --- entry point ------------------------------------------------------
    def parse_program(self) -> ast.Program:
        prog = ast.Program()
        while not self.at("EOF"):
            prog.nodes.append(self.parse_statement())
        return prog

    def parse_statement(self) -> ast.Node:
        t = self.peek()
        if t.kind != "IDENT":
            raise ParseError(f"line {t.line}, col {t.col}: expected a statement, got {t.value!r}")
        kw = t.value
        dispatch = {
            "jurisdiction": self._jurisdiction,
            "party": self._party,
            "fact": self._fact,
            "evidence": self._evidence,
            "claim": self._claim,
            "rule": self._rule,
            "obligation": lambda: self._deontic("obligation"),
            "permission": lambda: self._deontic("permission"),
            "prohibition": lambda: self._deontic("prohibition"),
            "constraint": self._constraint,
            "exclusive": self._exclusive,
            "assert": lambda: self._query("assert"),
            "prove": lambda: self._query("assert"),
            "refute": lambda: self._query("refute"),
            "explain": lambda: self._query("explain"),
            "discover": lambda: self._query("discover"),
        }
        if kw not in dispatch:
            raise ParseError(f"line {t.line}, col {t.col}: unknown statement keyword {kw!r}")
        return dispatch[kw]()

    # --- statements -------------------------------------------------------
    def _jurisdiction(self) -> ast.Jurisdiction:
        span = self._span()
        self.expect("IDENT", "jurisdiction")
        name = self.expect("IDENT").value
        return ast.Jurisdiction(name=name, span=span)

    def _party(self) -> ast.Party:
        span = self._span()
        self.expect("IDENT", "party")
        pid = self.expect("IDENT").value
        self.expect("PUNCT", "=")
        ptype = self.expect("IDENT").value
        label = self.expect("STRING").value
        return ast.Party(id=pid, type=ptype, label=label, span=span)

    def _fact(self) -> ast.Fact:
        span = self._span()
        self.expect("IDENT", "fact")
        fid = self.expect("IDENT").value
        self.expect("PUNCT", ":")
        ftype = self.expect("IDENT").value
        fields = self._record()
        prov = self._maybe_source()
        status_kw = "Alleged"
        if self.at_keyword("status"):
            self.next()
            status_kw = self.expect("IDENT").value
        return ast.Fact(id=fid, type=ftype, fields=fields, provenance=prov,
                        status_kw=status_kw, span=span)

    def _evidence(self) -> ast.Evidence:
        span = self._span()
        self.expect("IDENT", "evidence")
        eid = self.expect("IDENT").value
        self.expect("PUNCT", ":")
        etype = self.expect("IDENT").value
        fields = self._record()
        prov = self._maybe_source()
        supports = refutes = None
        if self.at_keyword("supports"):
            self.next()
            supports = self._predicate()
        elif self.at_keyword("refutes"):
            self.next()
            refutes = self._predicate()
        return ast.Evidence(id=eid, type=etype, fields=fields, provenance=prov,
                            supports=supports, refutes=refutes, span=span)

    def _claim(self) -> ast.Claim:
        span = self._span()
        self.expect("IDENT", "claim")
        cid = self.expect("IDENT").value
        self.expect("IDENT", "by")
        by = self.expect("IDENT").value
        self.expect("PUNCT", ":")
        text = self.expect("STRING").value
        self.expect("IDENT", "asserts")
        pred = self._predicate()
        return ast.Claim(id=cid, by=by, text=text, asserts=pred, span=span)

    def _rule(self) -> ast.Rule:
        span = self._span()
        self.expect("IDENT", "rule")
        rid = self.expect("IDENT").value
        self.expect("PUNCT", ":")
        head = self._predicate()
        if self.at_keyword("requires"):
            self.next()
            connective = "requires"
        elif self.at_keyword("established_if"):
            self.next()
            connective = "established_if"
        elif self.at_keyword("normally"):
            self.next()
            connective = "normally"
        else:
            t = self.peek()
            raise ParseError(
                f"line {t.line}, col {t.col}: expected 'requires', 'established_if', or 'normally'")
        body = self._predicate_list()
        # Defeasible defaults: `normally ... except when P except when Q`.
        exceptions: list[ast.Predicate] = []
        while self.at_keyword("except"):
            self.next()
            if self.at_keyword("when"):
                self.next()
            exceptions.append(self._predicate())
        return ast.Rule(id=rid, head=head, body=tuple(body), connective=connective,
                        span=span, exceptions=tuple(exceptions))

    def _deontic(self, modality: str) -> ast.Obligation:
        span = self._span()
        self.expect("IDENT", modality)
        oid = self.expect("IDENT").value
        fields = self._record()
        bearer = self._as_ref(fields.get("bearer"))
        counterparty = self._as_ref(fields.get("to"))
        that = fields.get("that")
        if not isinstance(that, ast.Predicate):
            raise ParseError(f"{modality} {oid!r}: field 'that:' must be a predicate")
        by_date = fields.get("by") if isinstance(fields.get("by"), ast.DateLit) else None
        on_breach = fields.get("on_breach") if isinstance(fields.get("on_breach"), ast.Predicate) else None
        return ast.Obligation(id=oid, modality=modality, bearer=bearer,
                              counterparty=counterparty, that=that, by_date=by_date,
                              on_breach=on_breach, span=span)

    def _constraint(self) -> ast.Constraint:
        span = self._span()
        self.expect("IDENT", "constraint")
        cid = self.expect("IDENT").value
        self.expect("PUNCT", ":")
        left = self._value()
        # Duration form: `left within N unit (of|before|after) right`.
        if self.at_keyword("within"):
            self.next()
            n = int(self.expect("NUMBER").value)
            unit = self.expect("IDENT").value
            if unit not in {"days", "weeks", "months", "years"}:
                raise ParseError(f"constraint {cid!r}: expected a unit (days/weeks/months/years), got {unit!r}")
            direction = self.expect("IDENT").value
            if direction not in {"of", "before", "after"}:
                raise ParseError(f"constraint {cid!r}: expected 'of', 'before', or 'after', got {direction!r}")
            right = self._value()
            return ast.Constraint(id=cid, left=left, op="within", right=right,
                                  span=span, n=n, unit=unit, direction=direction)
        op = self._constraint_op()
        right = self._value()
        return ast.Constraint(id=cid, left=left, op=op, right=right, span=span)

    def _constraint_op(self) -> str:
        t = self.peek()
        if t.kind == "PUNCT" and t.value in {"<=", ">=", "<", ">", "==", "!="}:
            return self.next().value
        if t.kind == "IDENT" and t.value in {"within", "before", "after", "equals"}:
            return self.next().value
        raise ParseError(f"line {t.line}, col {t.col}: expected a comparison operator")

    def _exclusive(self) -> ast.Exclusive:
        span = self._span()
        self.expect("IDENT", "exclusive")
        self.expect("PUNCT", "{")
        members = []
        while not self.at("PUNCT", "}"):
            members.append(self._predicate())
            if self.at("PUNCT", ","):
                self.next()
        self.expect("PUNCT", "}")
        return ast.Exclusive(members=tuple(members), span=span)

    def _query(self, kind: str) -> ast.Query:
        span = self._span()
        self.next()  # consume the query keyword
        target = self._predicate()
        standard = None
        for_party = None
        # Order-independent trailing modifiers.
        while self.at_keyword("under", "for"):
            if self.at_keyword("under"):
                self.next()
                standard = self.expect("IDENT").value
            else:
                self.next()
                for_party = self.expect("IDENT").value
        return ast.Query(kind=kind, target=target, standard=standard,
                         for_party=for_party, span=span)

    # --- shared sub-parsers ----------------------------------------------
    def _record(self) -> dict[str, ast.Value]:
        self.expect("PUNCT", "{")
        fields: dict[str, ast.Value] = {}
        while not self.at("PUNCT", "}"):
            key = self.expect("IDENT").value
            self.expect("PUNCT", ":")
            fields[key] = self._value()
            if self.at("PUNCT", ","):
                self.next()
        self.expect("PUNCT", "}")
        return fields

    def _maybe_source(self) -> ast.Provenance | None:
        if not self.at_keyword("from"):
            return None
        self.next()  # from
        self.expect("IDENT", "source")
        self.expect("PUNCT", "(")
        kv: dict[str, object] = {}
        while not self.at("PUNCT", ")"):
            key = self.expect("IDENT").value
            self.expect("PUNCT", "=")
            v = self._value()
            kv[key] = v
            if self.at("PUNCT", ","):
                self.next()
        self.expect("PUNCT", ")")

        def s(x):
            return x.name if isinstance(x, ast.Ref) else x

        def n(x):
            return int(x) if isinstance(x, float) else None

        return ast.Provenance(
            doc=s(kv.get("doc")),
            page=n(kv.get("page")),
            para=n(kv.get("para")),
            exhibit=s(kv.get("exhibit")),
            speaker=s(kv.get("speaker")),
        )

    def _predicate(self) -> ast.Predicate:
        name = self.expect("IDENT").value
        self.expect("PUNCT", "(")
        args: list[str] = []
        while not self.at("PUNCT", ")"):
            args.append(render_arg(self._value()))
            if self.at("PUNCT", ","):
                self.next()
        self.expect("PUNCT", ")")
        return ast.Predicate(name=name, args=tuple(args))

    def _predicate_list(self) -> list[ast.Predicate]:
        """Read predicates until the next top-level statement keyword."""
        preds: list[ast.Predicate] = []
        while True:
            # Skip connective words and commas used as separators.
            while self.at_keyword("and", "or") or self.at("PUNCT", ","):
                self.next()
            t = self.peek()
            # A predicate is IDENT immediately followed by '('. A statement
            # keyword (e.g. 'assert', 'rule') is IDENT followed by something
            # else — that terminates the body.
            if t.kind == "IDENT" and self.peek(1).kind == "PUNCT" and self.peek(1).value == "(":
                preds.append(self._predicate())
            else:
                break
        if not preds:
            raise ParseError(f"line {t.line}, col {t.col}: rule body has no predicates")
        return preds

    def _value(self) -> ast.Value:
        t = self.peek()
        if t.kind == "STRING":
            return self.next().value
        if t.kind == "DATE":
            return ast.DateLit(self.next().value)
        if t.kind == "NUMBER":
            return float(self.next().value)
        if t.kind == "IDENT":
            nxt = self.peek(1)
            if nxt.kind == "PUNCT" and nxt.value == "(":
                return self._predicate()
            if nxt.kind == "NUMBER" and t.value in _CURRENCIES:
                cur = self.next().value
                amt = float(self.next().value)
                return ast.Money(currency=cur, amount=amt)
            return ast.Ref(self.next().value)
        raise ParseError(f"line {t.line}, col {t.col}: expected a value, got {t.value!r}")

    @staticmethod
    def _as_ref(v) -> str | None:
        return v.name if isinstance(v, ast.Ref) else None


def render_arg(v: ast.Value) -> str:
    """Canonical string form of a predicate argument, for atom keys."""
    if isinstance(v, ast.Ref):
        return v.name
    if isinstance(v, ast.Money):
        return f"{v.currency}{v.amount:.0f}"
    if isinstance(v, ast.DateLit):
        return v.iso
    if isinstance(v, float):
        return f"{v:g}"
    if isinstance(v, ast.Predicate):
        return v.render()
    return str(v)


def parse(src: str) -> ast.Program:
    return Parser(tokenize(src)).parse_program()
