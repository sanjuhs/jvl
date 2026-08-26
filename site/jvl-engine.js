/* ============================================================================
   jvl-engine.js — a faithful in-browser port of the JVL reference compiler.

   Mirrors reference-impl/jvl/{lattice,lexer,parser,evaluator}.py closely enough
   that `JVL.run(src, cmd, arg)` prints the same thing the `jvl` CLI does. It is
   deliberately dependency-free and synchronous — a legal program is small, and
   this keeps the playground instant (no server round-trip, no WASM download).

   Exposes: window.JVL.run(source, command, arg) -> { text, ok }
            window.JVL.check(source) -> diagnostics
   ========================================================================== */
(function () {
  "use strict";

  // ---- lattice ----------------------------------------------------------
  var RANK = { REFUTED: 0, UNSUPPORTED: 1, UNKNOWN: 2, DISPUTED: 3, SUPPORTED: 4, PROVEN: 5, ESTABLISHED: 5 };
  var FACT_STATUS = {
    Established: "ESTABLISHED", Admitted: "ESTABLISHED", Proven: "PROVEN",
    Supported: "SUPPORTED", Alleged: "UNSUPPORTED", Disputed: "DISPUTED",
    Refuted: "REFUTED", Unknown: "UNKNOWN"
  };
  var STANDARD_THRESHOLD = { BalanceOfProbabilities: 4, ClearAndConvincing: 4, BeyondReasonableDoubt: 5 };

  function canonical(rank) { return rank === 5 ? "PROVEN" : nameOfRank(rank); }
  function nameOfRank(r) {
    for (var k in RANK) if (RANK[k] === r && k !== "ESTABLISHED") return k;
    return "UNKNOWN";
  }
  function meet(a, b) { return canonical(Math.min(RANK[a], RANK[b])); }
  function join(a, b) { return canonical(Math.max(RANK[a], RANK[b])); }
  function combine(statuses) {
    if (!statuses.length) return "UNKNOWN";
    var hasFor = statuses.some(function (s) { return RANK[s] >= 4; });
    var hasAgainst = statuses.some(function (s) { return s === "REFUTED"; });
    if (hasFor && hasAgainst) return "DISPUTED";
    var best = statuses.reduce(function (a, s) { return RANK[s] > RANK[a] ? s : a; }, statuses[0]);
    if (RANK[best] === 5) {
      if (statuses.indexOf("ESTABLISHED") >= 0 && statuses.indexOf("PROVEN") < 0) return "ESTABLISHED";
      return "PROVEN";
    }
    return best;
  }
  function meets(status, standard) {
    if (status === "DISPUTED") return false;
    return RANK[status] >= STANDARD_THRESHOLD[standard];
  }

  // ---- lexer ------------------------------------------------------------
  var SPEC = [
    ["SKIP", /^[ \t\r]+/],
    ["NEWLINE", /^\n/],
    ["COMMENT", /^(?:#|\/\/)[^\n]*/],
    ["DATE", /^\d{4}-\d{2}-\d{2}/],
    ["NUMBER", /^\d[\d_]*(?:\.\d+)?/],
    ["STRING", /^"(?:[^"\\]|\\.)*"/],
    ["IDENT", /^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z0-9_]+)*/],
    ["PUNCT", /^(?:<=|>=|==|!=|[{}():,=<>])/]
  ];
  function tokenize(src) {
    var toks = [], line = 1, i = 0;
    while (i < src.length) {
      var rest = src.slice(i), matched = false;
      for (var s = 0; s < SPEC.length; s++) {
        var m = SPEC[s][1].exec(rest);
        if (!m) continue;
        var kind = SPEC[s][0], text = m[0];
        if (kind === "NEWLINE") line++;
        else if (kind !== "SKIP" && kind !== "COMMENT") {
          if (kind === "STRING") toks.push({ kind: "STRING", value: text.slice(1, -1), line: line });
          else if (kind === "NUMBER") toks.push({ kind: "NUMBER", value: text.replace(/_/g, ""), line: line });
          else toks.push({ kind: kind, value: text, line: line });
        }
        i += text.length; matched = true; break;
      }
      if (!matched) throw new Error("Lex error: unexpected '" + src[i] + "' at line " + line);
    }
    toks.push({ kind: "EOF", value: "", line: line });
    return toks;
  }

  // ---- parser -----------------------------------------------------------
  var STMT_KW = ["jurisdiction", "party", "fact", "evidence", "claim", "rule",
    "obligation", "permission", "prohibition", "constraint", "exclusive",
    "assert", "prove", "refute", "explain", "discover"];
  var CURRENCIES = ["INR", "USD", "EUR", "GBP", "JPY", "AUD", "CAD", "SGD", "CNY", "CHF"];

  function Parser(toks) { this.t = toks; this.i = 0; }
  Parser.prototype.peek = function (k) { return this.t[Math.min(this.i + (k || 0), this.t.length - 1)]; };
  Parser.prototype.next = function () { var x = this.t[this.i]; if (this.i < this.t.length - 1) this.i++; return x; };
  Parser.prototype.at = function (kind, val) { var t = this.peek(); return t.kind === kind && (val === undefined || t.value === val); };
  Parser.prototype.atKw = function () { var t = this.peek(); return t.kind === "IDENT" && Array.prototype.indexOf.call(arguments, t.value) >= 0; };
  Parser.prototype.expect = function (kind, val) {
    var t = this.peek();
    if (t.kind !== kind || (val !== undefined && t.value !== val))
      throw new Error("Parse error line " + t.line + ": expected " + (val || kind) + ", got '" + t.value + "'");
    return this.next();
  };
  Parser.prototype.program = function () {
    var nodes = [];
    while (!this.at("EOF")) nodes.push(this.statement());
    return nodes;
  };
  Parser.prototype.statement = function () {
    var t = this.peek();
    if (t.kind !== "IDENT") throw new Error("Parse error line " + t.line + ": expected a statement, got '" + t.value + "'");
    switch (t.value) {
      case "jurisdiction": this.next(); return { type: "jurisdiction", name: this.expect("IDENT").value };
      case "party": return this.party();
      case "fact": return this.fact();
      case "evidence": return this.evidence();
      case "claim": return this.claim();
      case "rule": return this.rule();
      case "obligation": case "permission": case "prohibition": return this.deontic(t.value);
      case "constraint": return this.constraint();
      case "exclusive": return this.exclusive();
      case "assert": case "prove": this.next(); return this.query("assert");
      case "refute": this.next(); return this.query("refute");
      case "explain": this.next(); return this.query("explain");
      case "discover": this.next(); return this.query("discover");
      default: throw new Error("Parse error line " + t.line + ": unknown keyword '" + t.value + "'");
    }
  };
  Parser.prototype.party = function () {
    this.expect("IDENT", "party"); var id = this.expect("IDENT").value;
    this.expect("PUNCT", "="); var type = this.expect("IDENT").value; var label = this.expect("STRING").value;
    return { type: "party", id: id, ptype: type, label: label };
  };
  Parser.prototype.fact = function () {
    this.expect("IDENT", "fact"); var id = this.expect("IDENT").value;
    this.expect("PUNCT", ":"); var ftype = this.expect("IDENT").value;
    var fields = this.record(); var prov = this.maybeSource(); var status = "Alleged";
    if (this.atKw("status")) { this.next(); status = this.expect("IDENT").value; }
    return { type: "fact", id: id, ftype: ftype, fields: fields, prov: prov, status: status };
  };
  Parser.prototype.evidence = function () {
    this.expect("IDENT", "evidence"); var id = this.expect("IDENT").value;
    this.expect("PUNCT", ":"); var etype = this.expect("IDENT").value;
    var fields = this.record(); var prov = this.maybeSource(); var supports = null, refutes = null;
    if (this.atKw("supports")) { this.next(); supports = this.predicate(); }
    else if (this.atKw("refutes")) { this.next(); refutes = this.predicate(); }
    return { type: "evidence", id: id, etype: etype, fields: fields, prov: prov, supports: supports, refutes: refutes };
  };
  Parser.prototype.claim = function () {
    this.expect("IDENT", "claim"); var id = this.expect("IDENT").value;
    this.expect("IDENT", "by"); var by = this.expect("IDENT").value;
    this.expect("PUNCT", ":"); var text = this.expect("STRING").value;
    this.expect("IDENT", "asserts"); var pred = this.predicate();
    return { type: "claim", id: id, by: by, text: text, asserts: pred };
  };
  Parser.prototype.rule = function () {
    this.expect("IDENT", "rule"); var id = this.expect("IDENT").value; this.expect("PUNCT", ":");
    var head = this.predicate(); var conn;
    if (this.atKw("requires")) { this.next(); conn = "requires"; }
    else if (this.atKw("established_if")) { this.next(); conn = "established_if"; }
    else if (this.atKw("normally")) { this.next(); conn = "normally"; }
    else throw new Error("Parse error line " + this.peek().line + ": expected 'requires' or 'established_if'");
    var body = this.predicateList();
    var exceptions = [];
    while (this.atKw("except")) { this.next(); if (this.atKw("when")) this.next(); exceptions.push(this.predicate()); }
    return { type: "rule", id: id, head: head, body: body, conn: conn, exceptions: exceptions };
  };
  Parser.prototype.deontic = function (modality) {
    this.expect("IDENT", modality); var id = this.expect("IDENT").value; var fields = this.record();
    return { type: "deontic", modality: modality, id: id, fields: fields };
  };
  Parser.prototype.constraint = function () {
    this.expect("IDENT", "constraint"); var id = this.expect("IDENT").value; this.expect("PUNCT", ":");
    var left = this.value(); var op = this.constraintOp(); var right = this.value();
    return { type: "constraint", id: id, left: left, op: op, right: right };
  };
  Parser.prototype.constraintOp = function () {
    var t = this.peek();
    if (t.kind === "PUNCT" && ["<=", ">=", "<", ">", "==", "!="].indexOf(t.value) >= 0) return this.next().value;
    if (t.kind === "IDENT" && ["within", "before", "after", "equals"].indexOf(t.value) >= 0) return this.next().value;
    throw new Error("Parse error line " + t.line + ": expected a comparison operator");
  };
  Parser.prototype.exclusive = function () {
    this.expect("IDENT", "exclusive"); this.expect("PUNCT", "{"); var members = [];
    while (!this.at("PUNCT", "}")) { members.push(this.predicate()); if (this.at("PUNCT", ",")) this.next(); }
    this.expect("PUNCT", "}"); return { type: "exclusive", members: members };
  };
  Parser.prototype.query = function (kind) {
    var target = this.predicate(); var standard = null, forParty = null;
    while (this.atKw("under", "for")) {
      if (this.atKw("under")) { this.next(); standard = this.expect("IDENT").value; }
      else { this.next(); forParty = this.expect("IDENT").value; }
    }
    return { type: "query", kind: kind, target: target, standard: standard, forParty: forParty };
  };
  Parser.prototype.record = function () {
    this.expect("PUNCT", "{"); var fields = {};
    while (!this.at("PUNCT", "}")) {
      var key = this.expect("IDENT").value; this.expect("PUNCT", ":"); fields[key] = this.value();
      if (this.at("PUNCT", ",")) this.next();
    }
    this.expect("PUNCT", "}"); return fields;
  };
  Parser.prototype.maybeSource = function () {
    if (!this.atKw("from")) return null;
    this.next(); this.expect("IDENT", "source"); this.expect("PUNCT", "("); var kv = {};
    while (!this.at("PUNCT", ")")) {
      var key = this.expect("IDENT").value; this.expect("PUNCT", "="); kv[key] = this.value();
      if (this.at("PUNCT", ",")) this.next();
    }
    this.expect("PUNCT", ")");
    function s(x) { return x && x.ref ? x.ref : x; }
    function n(x) { return typeof x === "number" ? Math.round(x) : null; }
    return { doc: s(kv.doc), page: n(kv.page), para: n(kv.para), exhibit: s(kv.exhibit), speaker: s(kv.speaker) };
  };
  Parser.prototype.predicate = function () {
    var name = this.expect("IDENT").value; this.expect("PUNCT", "("); var args = [];
    while (!this.at("PUNCT", ")")) { args.push(renderArg(this.value())); if (this.at("PUNCT", ",")) this.next(); }
    this.expect("PUNCT", ")"); return { name: name, args: args };
  };
  Parser.prototype.predicateList = function () {
    var preds = [];
    while (true) {
      while (this.atKw("and", "or") || this.at("PUNCT", ",")) this.next();
      var t = this.peek();
      if (t.kind === "IDENT" && this.peek(1).kind === "PUNCT" && this.peek(1).value === "(") preds.push(this.predicate());
      else break;
    }
    if (!preds.length) throw new Error("Parse error line " + this.peek().line + ": rule body has no predicates");
    return preds;
  };
  Parser.prototype.value = function () {
    var t = this.peek();
    if (t.kind === "STRING") return this.next().value;
    if (t.kind === "DATE") return { date: this.next().value };
    if (t.kind === "NUMBER") return parseFloat(this.next().value);
    if (t.kind === "IDENT") {
      var nx = this.peek(1);
      if (nx.kind === "PUNCT" && nx.value === "(") return this.predicate();
      if (nx.kind === "NUMBER" && CURRENCIES.indexOf(t.value) >= 0) { var cur = this.next().value; return { currency: cur, amount: parseFloat(this.next().value) }; }
      return { ref: this.next().value };
    }
    throw new Error("Parse error line " + t.line + ": expected a value, got '" + t.value + "'");
  };

  function renderArg(v) {
    if (v && v.ref) return v.ref;
    if (v && v.currency) return v.currency + Math.round(v.amount);
    if (v && v.date) return v.date;
    if (v && v.name) return renderPred(v);
    if (typeof v === "number") return String(v);
    return String(v);
  }
  function renderPred(p) { return p.name + "(" + p.args.join(", ") + ")"; }
  function keyOf(p) { return p.name + "|" + p.args.join(","); }
  function renderProv(p) {
    if (!p) return "(no source)";
    var b = [];
    if (p.doc) b.push(p.doc);
    if (p.page != null) b.push("p." + p.page);
    if (p.para != null) b.push("¶" + p.para);
    if (p.exhibit) b.push("[" + p.exhibit + "]");
    if (p.speaker) b.push("by " + p.speaker);
    return b.length ? b.join(" ") : "(no source)";
  }

  // ---- evaluator --------------------------------------------------------
  var VAR = /^[a-z][A-Za-z0-9_]*$/;
  function Evaluator(nodes) { this.nodes = nodes; this.constants = {}; this.base = {}; this.atoms = {}; this.status = {}; }
  Evaluator.prototype.ofType = function (t) { return this.nodes.filter(function (n) { return n.type === t; }); };
  Evaluator.prototype.build = function () {
    var self = this;
    this.nodes.forEach(function (n) {
      if (["party", "fact", "evidence", "claim"].indexOf(n.type) >= 0) self.constants[n.id] = true;
    });
    this.nodes.forEach(function (n) {
      if (n.type === "fact") self.addBase(n.ftype + "|" + n.id, { kind: "fact", src: n.id, status: FACT_STATUS[n.status] || "UNSUPPORTED", prov: n.prov, note: n.status + " fact" });
      else if (n.type === "evidence") {
        if (n.supports) self.addBase(keyOf(n.supports), { kind: "evidence", src: n.id, status: "SUPPORTED", prov: n.prov, note: "supporting evidence" });
        if (n.refutes) self.addBase(keyOf(n.refutes), { kind: "evidence", src: n.id, status: "REFUTED", prov: n.prov, note: "refuting evidence" });
      } else if (n.type === "claim") self.addBase(keyOf(n.asserts), { kind: "claim", src: n.id, status: "UNSUPPORTED", prov: null, note: "claimed by " + n.by });
    });
    this.fixpoint();
    return this;
  };
  Evaluator.prototype.addBase = function (key, c) { (this.base[key] = this.base[key] || []).push(c); };
  Evaluator.prototype.varsOf = function (rule) {
    var self = this, vs = {};
    [rule.head].concat(rule.body).concat(rule.exceptions || []).forEach(function (p) {
      p.args.forEach(function (a) { if (!self.constants[a] && VAR.test(a)) vs[a] = true; });
    });
    return Object.keys(vs);
  };
  Evaluator.prototype.fixpoint = function () {
    var self = this, rules = this.ofType("rule"), prev = {};
    var universe = Object.keys(this.constants);
    for (var pass = 0; pass < 100; pass++) {
      var atoms = {};
      Object.keys(this.base).forEach(function (k) { atoms[k] = self.base[k].slice(); });
      rules.forEach(function (rule) {
        self.bindings(rule, prev, universe).forEach(function (binding) {
          var fired = self.fire(rule, binding, prev);
          if (fired.status === null) return;
          (atoms[fired.head] = atoms[fired.head] || []).push({ kind: "rule", src: rule.id, status: fired.status, note: rule.conn });
        });
      });
      var newStatus = {};
      Object.keys(atoms).forEach(function (k) { newStatus[k] = combine(atoms[k].map(function (c) { return c.status; })); });
      if (JSON.stringify(newStatus) === JSON.stringify(prev)) { this._atoms = atoms; this.status = newStatus; return; }
      prev = newStatus;
      this._atoms = atoms; this.status = newStatus;
    }
  };
  Evaluator.prototype.bindings = function (rule, prev, universe) {
    var vars = this.varsOf(rule).sort();
    if (!vars.length) return [{}];
    // Index known atoms (from the previous pass + the base facts) by predicate.
    var index = {};
    function add(key) { var p = key.split("|"); (index[p[0]] = index[p[0]] || []).push(p[1] ? p[1].split(",") : []); }
    Object.keys(prev).forEach(add);
    Object.keys(this.base).forEach(function (k) { if (!(k in prev)) add(k); });
    // Collect the values each variable actually takes — linear, no cartesian
    // product over the universe, no quadratic join between body predicates.
    var cand = {}; vars.forEach(function (v) { cand[v] = {}; });
    (rule.body || []).concat(rule.exceptions || []).forEach(function (pred) {
      var atoms = index[pred.name]; if (!atoms) return;
      atoms.forEach(function (args) {
        if (args.length !== pred.args.length) return;
        for (var i = 0; i < args.length; i++) {
          var h = pred.args[i];
          if (vars.indexOf(h) < 0 && h !== args[i]) return; // constant mismatch
        }
        for (var j = 0; j < args.length; j++) {
          var hv = pred.args[j];
          if (vars.indexOf(hv) >= 0) cand[hv][args[j]] = true;
        }
      });
    });
    var valueLists = vars.map(function (v) {
      var ks = Object.keys(cand[v]); return ks.length ? ks : universe;
    });
    var out = [], combos = [[]];
    valueLists.forEach(function (vals) {
      var next = [];
      combos.forEach(function (c) { vals.forEach(function (u) { next.push(c.concat([u])); }); });
      combos = next.length > 10000 ? next.slice(0, 10000) : next;
    });
    combos.forEach(function (c) { var b = {}; vars.forEach(function (v, i) { b[v] = c[i]; }); out.push(b); });
    return out;
  };
  Evaluator.prototype.fire = function (rule, binding, prev) {
    function inst(p) { return p.name + "|" + p.args.map(function (a) { return binding[a] || a; }).join(","); }
    var headKey = inst(rule.head);
    var bodyKeys = rule.body.map(inst);
    var bodyStatuses = bodyKeys.map(function (k) { return prev[k] || "UNKNOWN"; });
    if (bodyStatuses.every(function (s) { return s === "UNKNOWN"; })) return { head: headKey, status: null };
    var acc = bodyStatuses[0];
    for (var i = 1; i < bodyStatuses.length; i++) acc = (rule.conn === "established_if") ? join(acc, bodyStatuses[i]) : meet(acc, bodyStatuses[i]);
    // default logic: an exception that holds defeats the (normally) conclusion.
    if ((rule.conn === "normally") && rule.exceptions && rule.exceptions.length) {
      var defeated = rule.exceptions.some(function (ex) {
        var exKey = ex.name + "|" + ex.args.map(function (a) { return binding[a] || a; }).join(",");
        return RANK[prev[exKey] || "UNKNOWN"] >= 4;
      });
      if (defeated) acc = "REFUTED";
    }
    return { head: headKey, status: acc };
  };
  Evaluator.prototype.atomStatus = function (key) { return this.status[key] || "UNKNOWN"; };

  function unify(head, key) {
    var parts = key.split("|"), name = parts[0], args = parts[1] ? parts[1].split(",") : [];
    if (head.name !== name || head.args.length !== args.length) return null;
    var b = {};
    for (var i = 0; i < head.args.length; i++) {
      var h = head.args[i], a = args[i];
      if (VAR.test(h)) { if (b[h] !== undefined && b[h] !== a) return null; b[h] = a; }
      else if (h !== a) return null;
    }
    return b;
  }

  Evaluator.prototype.trace = function (target, depth, seen) {
    depth = depth || 0; seen = seen || {};
    var self = this, key = keyOf(target), st = this.atomStatus(key), pad = "  ".repeat(depth);
    var label = renderPred(target);
    var width = Math.max(4, 46 - label.length - depth * 2);
    var lines = [pad + label + " " + ".".repeat(width) + " " + st];
    if (seen[key]) return lines;
    seen = Object.assign({}, seen); seen[key] = true;
    (this._atoms[key] || []).forEach(function (c) {
      if (c.kind === "rule") return;
      var prov = c.prov ? "  →  " + renderProv(c.prov) : "";
      lines.push(pad + "  └─ " + c.note + " (" + c.src + ")" + prov);
    });
    this.ofType("rule").forEach(function (rule) {
      var binding = unify(rule.head, key);
      if (!binding) return;
      var body = rule.body.map(function (p) { return { name: p.name, args: p.args.map(function (a) { return binding[a] || a; }) }; });
      var sep = rule.conn === "requires" ? " ∧ " : (rule.conn === "established_if" ? " ∨ " : " ⇒ ");
      lines.push(pad + "  └─ " + rule.conn + ": " + body.map(renderPred).join(sep));
      body.forEach(function (b) { lines = lines.concat(self.trace(b, depth + 2, seen)); });
    });
    return lines;
  };
  Evaluator.prototype.discover = function (target) {
    var self = this, out = [], key = keyOf(target);
    this.ofType("rule").forEach(function (rule) {
      var binding = unify(rule.head, key);
      if (!binding) return;
      rule.body.forEach(function (p) {
        var bp = { name: p.name, args: p.args.map(function (a) { return binding[a] || a; }) };
        var st = self.atomStatus(keyOf(bp));
        if (RANK[st] < 4) out.push([bp, st]);
      });
    });
    return out;
  };
  Evaluator.prototype.contradictions = function () {
    var self = this, out = [];
    Object.keys(this.status).forEach(function (k) {
      if (self.status[k] === "DISPUTED") { var p = k.split("|"); out.push("DISPUTED: " + p[0] + "(" + (p[1] || "") + ") has support and refutation on the record"); }
    });
    this.ofType("exclusive").forEach(function (ex) {
      var live = ex.members.filter(function (m) { return RANK[self.atomStatus(keyOf(m))] >= 4; });
      if (live.length >= 2) out.push("MUTUAL EXCLUSION VIOLATED: " + live.map(renderPred).join(", ") + " cannot all hold");
    });
    return out;
  };
  Evaluator.prototype.resolve = function (v) {
    if (v && (v.currency || v.date)) return v;
    if (typeof v === "number") return v;
    if (v && v.ref && v.ref.indexOf(".") >= 0) {
      var parts = v.ref.split("."), fid = parts[0], fld = parts[1];
      var fact = this.ofType("fact").filter(function (f) { return f.id === fid; })[0];
      if (!fact || !(fld in fact.fields)) return null;
      return fact.fields[fld];
    }
    return null;
  };
  Evaluator.prototype.constraints = function () {
    var self = this;
    return this.ofType("constraint").map(function (c) {
      var l = self.resolve(c.left), r = self.resolve(c.right);
      if (l == null || r == null) return { id: c.id, ok: null, note: "unresolved operand" };
      if (l.currency && r.currency) { if (l.currency !== r.currency) return { id: c.id, ok: null, note: "currency mismatch" }; return { id: c.id, ok: cmp(l.amount, r.amount, c.op) }; }
      if (l.date && r.date) return { id: c.id, ok: cmpDate(l.date, r.date, c.op) };
      if (typeof l === "number" && typeof r === "number") return { id: c.id, ok: cmp(l, r, c.op) };
      return { id: c.id, ok: null, note: "not comparable" };
    });
  };
  function cmp(a, b, op) { return ({ "<=": a <= b, ">=": a >= b, "<": a < b, ">": a > b, "==": a === b, "!=": a !== b, "equals": a === b })[op]; }
  function cmpDate(a, b, op) { if (op === "before") return a < b; if (op === "after") return a > b; return cmp(a, b, op); }

  Evaluator.prototype.staticCheck = function () {
    var self = this, diags = [], parties = {};
    this.ofType("party").forEach(function (p) { parties[p.id] = true; });
    this.nodes.forEach(function (n) {
      if (n.type === "fact" && !n.prov) diags.push({ level: "warning", msg: "fact '" + n.id + "' has no source(...) — provenance is required for a trustworthy conclusion" });
      if (n.type === "evidence" && !n.prov) diags.push({ level: "warning", msg: "evidence '" + n.id + "' has no source(...)" });
      if (n.type === "claim" && !parties[n.by]) diags.push({ level: "error", msg: "claim '" + n.id + "' is by undeclared party '" + n.by + "'" });
      if (n.type === "query" && n.standard && !(n.standard in STANDARD_THRESHOLD)) diags.push({ level: "error", msg: "unknown standard of proof '" + n.standard + "'" });
    });
    return diags;
  };

  // ---- command runner ---------------------------------------------------
  function contestingClaims(nodes, target) {
    var out = [];
    nodes.filter(function (n) { return n.type === "claim"; }).forEach(function (cl) {
      if (cl.asserts.name === target.name && cl.asserts.args.join() === target.args.join()) return;
      if (target.args.some(function (a) { return cl.asserts.args.indexOf(a) >= 0; })) out.push("claim " + cl.id + " (" + cl.by + ": " + renderPred(cl.asserts) + ")");
    });
    return out.join("; ");
  }

  function run(source, command, arg) {
    var nodes, ev;
    try { nodes = new Parser(tokenize(source)).program(); }
    catch (e) { return { text: "error: " + e.message, ok: false }; }
    try { ev = new Evaluator(nodes).build(); }
    catch (e) { return { text: "error: " + e.message, ok: false }; }
    var L = [];
    command = command || "run";

    if (command === "check" || command === "run") {
      var diags = ev.staticCheck();
      var errors = diags.filter(function (d) { return d.level === "error"; });
      diags.forEach(function (d) { L.push("[" + d.level + "] " + d.msg); });
      L.push((errors.length ? "✗" : "✓") + " check: " + errors.length + " error(s), " + (diags.length - errors.length) + " warning(s)");
      if (command === "check") return { text: L.join("\n"), ok: errors.length === 0 };
      L.push("");
    }
    if (command === "run" || command === "assert") {
      var queries = ev.ofType("query").filter(function (q) { return q.kind === "assert" || q.kind === "refute"; });
      if (!queries.length && command === "assert") return { text: "no assert/refute statements in file", ok: true };
      queries.forEach(function (q) {
        var std = q.standard || "BalanceOfProbabilities";
        var st = ev.atomStatus(keyOf(q.target)), passes = meets(st, std);
        L.push("⚖  " + q.kind + "  " + renderPred(q.target) + "   standard: " + std); L.push("");
        ev.trace(q.target).forEach(function (line) { L.push("  " + line); });
        var ok = q.kind === "assert" ? passes : st === "REFUTED";
        L.push(""); L.push("  RESULT: " + st + "  " + (ok ? "✓" : "✗") + " (" + (passes ? "meets" : "does not meet") + " " + std + ")");
        var others = contestingClaims(nodes, q.target);
        if (others) L.push("  NOTE:   contested by " + others);
        L.push("");
      });
      return { text: L.join("\n").replace(/\n+$/, ""), ok: true };
    }
    if (command === "explain" || command === "discover") {
      var target;
      try { target = new Parser(tokenize("explain " + arg)).program()[0].target; }
      catch (e) { return { text: "error: bad predicate '" + arg + "'", ok: false }; }
      if (command === "explain") {
        L.push("⚖  explain  " + renderPred(target)); L.push("");
        ev.trace(target).forEach(function (line) { L.push("  " + line); });
        return { text: L.join("\n"), ok: true };
      }
      L.push("⚖  discover  what is missing for " + renderPred(target)); L.push("");
      var missing = ev.discover(target);
      if (!missing.length) L.push("  nothing missing — every element is at least SUPPORTED");
      else missing.forEach(function (m) { L.push("  ✗ " + renderPred(m[0]) + " — " + m[1]); });
      return { text: L.join("\n"), ok: true };
    }
    if (command === "contradictions") {
      L.push("⚖  contradiction check"); L.push("");
      var issues = ev.contradictions();
      if (!issues.length) L.push("  ✓ no contradictions detected among the clauses");
      else issues.forEach(function (i) { L.push("  ⚠ " + i); });
      return { text: L.join("\n"), ok: issues.length === 0 };
    }
    if (command === "constraints") {
      L.push("⚖  objective constraints"); L.push("");
      var results = ev.constraints();
      if (!results.length) L.push("  (no constraints declared)");
      results.forEach(function (r) {
        if (r.ok === null) L.push("  ? " + r.id + ": " + (r.note || "unresolved"));
        else if (r.ok) L.push("  ✓ " + r.id + ": holds");
        else L.push("  ✗ " + r.id + ": VIOLATED");
      });
      return { text: L.join("\n"), ok: true };
    }
    return { text: "unknown command: " + command, ok: false };
  }

  window.JVL = { run: run, tokenize: tokenize, version: "0.3.0-js" };
})();
