/* editor.js — the interactive LVL editor: live highlight, run, lessons, AI. */
(function () {
  "use strict";

  var LESSONS = [
    {
      id: "hello", title: "1 · Hello, dispute",
      note: "A complete program. Declare parties, state a fact with its source, add a claim and a piece of evidence, write two rules, and ask a question. Hit ▶ Run.",
      pred: "Loan(transfer_17)",
      code: `jurisdiction IN.Contract.v1

party A = Person "Anil Kumar"
party B = Person "Beena Rao"

fact transfer_17 : TransferOfValue {
    from: A  to: B  amount: INR 1_000_000  on: 2025-03-10
} from source(doc="BankStatement_3", page=2, para=4) status Established

claim c_loan by A : "the transfer was a loan" asserts Loan(transfer_17)

evidence w17 : Message { author: B  text: "I'll repay you next month." }
    from source(doc="WhatsApp_17", para=21) supports RepaymentObligation(transfer_17)

rule loan_definition:
    Loan(t) requires TransferOfValue(t) RepaymentObligation(t)
rule repayment_obligation:
    RepaymentObligation(t) established_if AdmittedRepayment(t) or ContractRequiresRepayment(t)

assert Loan(transfer_17) under BalanceOfProbabilities`
    },
    {
      id: "provenance", title: "2 · Facts & provenance",
      note: "Every fact should carry a source(...). Delete the `from source(...)` part and hit Check — the compiler warns you. A fact with no source is not trustworthy.",
      pred: "TransferOfValue(t1)",
      code: `party A = Person "Payer"
party B = Person "Payee"

fact t1 : TransferOfValue {
    from: A  to: B  amount: INR 500_000  on: 2025-02-01
} from source(doc="Ledger", page=7, para=3) status Established

assert TransferOfValue(t1) under BalanceOfProbabilities`
    },
    {
      id: "standards", title: "3 · Standards of proof",
      note: "The same evidence can pass a civil case and fail a criminal one. One element here (the mental element) has no evidence — so under BeyondReasonableDoubt the offence can't be certified. Try Discover with Cheating(payment).",
      pred: "Cheating(payment)",
      code: `party accused = Person "Accused"

fact payment : DeliveryOfProperty { amount: INR 2_500_000 }
    from source(doc="FIR", page=1, para=3) status Established

rule cheating:
    Cheating(p) requires
        Deception(p) DishonestInducement(p)
        DeliveryOfProperty(p) DishonestIntentionAtInception(p)

evidence brochure : Document { note: "fabricated projection" }
    from source(doc="Exhibit_P3", para=8) supports Deception(payment)
evidence promise : Message { author: accused  text: "guaranteed 40% returns" }
    from source(doc="WhatsApp_22", para=5) supports DishonestInducement(payment)

assert Cheating(payment) under BeyondReasonableDoubt`
    },
    {
      id: "conflict", title: "4 · Contradictions",
      note: "Evidence that supports AND refutes the same proposition makes it Disputed — and a Disputed proposition never meets a standard. Hit Contradictions.",
      pred: "PresentAtScene(accused)",
      code: `party accused = Person "Accused"

evidence witness : Testimony { text: "I saw the accused at the scene." }
    from source(doc="Deposition", para=14) supports PresentAtScene(accused)

evidence alibi : Record { note: "boarding pass places accused abroad" }
    from source(doc="Exhibit_D2", para=2) refutes PresentAtScene(accused)

assert PresentAtScene(accused) under BalanceOfProbabilities`
    },
    {
      id: "exclusive", title: "5 · Mutually exclusive",
      note: "Two characterisations that can't both be true. If both ever become Supported, `exclusive` flags a violation. Add a supporting evidence for Investment and re-check contradictions.",
      pred: "Loan(x)",
      code: `party A = Person "A"
party B = Person "B"

fact x : TransferOfValue { amount: INR 1_000_000 }
    from source(doc="Bank", page=1) status Established

claim c1 by A : "loan"       asserts Loan(x)
claim c2 by B : "investment" asserts Investment(x)
exclusive { Loan(x) Investment(x) }

evidence e1 : Message { text: "I'll repay you" }
    from source(doc="Chat", para=3) supports RepaymentObligation(x)

rule loan_def: Loan(t) requires TransferOfValue(t) RepaymentObligation(t)

assert Loan(x) under BalanceOfProbabilities`
    },
    {
      id: "default", title: "7 · Default logic",
      note: "Statutes are full of 'normally X, except when Y'. Here a late claim is normally time-barred — UNLESS the debt was acknowledged in time, which rebuts the default. Run it (TimeBarred is REFUTED), then delete the `ack` evidence and re-run.",
      pred: "TimeBarred(claim1)",
      code: `party creditor = Person "Creditor"
party debtor   = Person "Debtor"

fact claim1 : DebtClaim { principal: INR 300_000 }
    from source(doc="Plaint", page=1, para=2) status Established

evidence late : Record { note: "filed outside the 3-year window" }
    from source(doc="Plaint", page=1, para=5) supports FiledAfterLimitation(claim1)

evidence ack : Message { author: debtor  text: "I acknowledge the amount owed." }
    from source(doc="Email_2023", para=1) supports AcknowledgedWithinPeriod(claim1)

rule limitation_default:
    TimeBarred(c) normally
        FiledAfterLimitation(c)
    except when AcknowledgedWithinPeriod(c)

assert TimeBarred(claim1) under BalanceOfProbabilities`
    },
    {
      id: "constraints", title: "8 · Objective checks",
      note: "Money and dates need no legal judgement — just arithmetic. Here the claimed damages exceed the contractual cap. Hit Constraints.",
      pred: "",
      code: `fact nda : Agreement {
    penalty_cap: INR 5_000_000  expires_on: 2028-01-15
} from source(doc="NDA", page=1) status Established

fact breach : Disclosure {
    on: 2025-06-20  amount: INR 8_000_000
} from source(doc="Complaint", page=3, para=12) status Alleged

constraint damages_within_cap: breach.amount <= nda.penalty_cap
constraint within_term: breach.on before nda.expires_on`
    }
  ];

  var $ = function (s) { return document.querySelector(s); };
  var src = $("#src"), hl = $("#hl"), out = $("#out"), outName = $("#outName"), predInput = $("#predInput");
  var HL = window.LVLHL, LVL = window.LVL;

  function syncHighlight() {
    hl.innerHTML = HL.highlightLVL(src.value) + "\n";
  }
  function syncScroll() { hl.parentNode.scrollTop = src.scrollTop; hl.parentNode.scrollLeft = src.scrollLeft; }

  function loadLesson(l) {
    src.value = l.code; syncHighlight();
    $("#lessonNote").textContent = l.note;
    if (l.pred) predInput.value = l.pred;
    document.querySelectorAll("#lessons .tab").forEach(function (t) {
      t.classList.toggle("active", t.getAttribute("data-lesson") === l.id);
    });
    runCommand("run");
  }

  var graphOut = document.getElementById("graphOut");
  var outPre = out.parentNode; // the <pre> wrapping #out

  function runCommand(cmd, usePred) {
    var arg = usePred ? predInput.value.trim() : null;
    var res = LVL.run(src.value, cmd, arg);
    outName.textContent = "$ lvl " + (cmd === "graph" ? "emit graph" : cmd) + (arg ? ' "' + arg + '"' : "");

    if (cmd === "graph") {
      outPre.style.display = "none";
      graphOut.style.display = "block";
      graphOut.innerHTML = '<span class="o-dim">rendering…</span>';
      if (window.mermaid) {
        try {
          window.mermaid.render("g" + Date.now(), res.text).then(function (o) {
            graphOut.innerHTML = o.svg;
          }).catch(function (e) {
            graphOut.innerHTML = '<pre class="term"><span class="o-bad">graph error: ' + HL.esc(String(e && e.message || e)) + "</span>\n\n" + HL.esc(res.text) + "</pre>";
          });
        } catch (e) {
          graphOut.innerHTML = '<pre class="term">' + HL.esc(res.text) + "</pre>";
        }
      } else {
        graphOut.innerHTML = '<pre class="term">' + HL.esc(res.text) + "</pre>";
      }
      return;
    }
    outPre.style.display = "";
    graphOut.style.display = "none";
    // JSON output is shown verbatim; everything else gets terminal colorizing.
    out.innerHTML = cmd === "emit" ? HL.esc(res.text || "") : HL.colorizeTerm(res.text || "(no output)");
  }

  // ---- AI helper --------------------------------------------------------
  function fallbackPrompt(userText) {
    return "You are an LVL (Legal Verifiable Language) extractor. Convert the scenario below into a single LVL program.\n" +
      "Rules: every fact/evidence needs a from source(...); use party/fact/evidence/claim/rule/constraint/assert; " +
      "predicates are UpperCamelCase; never inflate confidence; leave unsupported elements unstated; end with assert ... under a standard.\n\n" +
      "Scenario:\n" + userText + "\n\nOutput only a fenced ```lvl code block.";
  }

  function initAI() {
    var btn = $("#aiBtn"), prompt = $("#aiPrompt"), status = $("#aiStatus");
    btn.addEventListener("click", function () {
      var text = prompt.value.trim();
      if (!text) { status.textContent = "Describe a scenario first."; return; }
      status.textContent = "Thinking…"; btn.disabled = true;
      fetch("/api/assist", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: text })
      }).then(function (r) {
        if (!r.ok) throw new Error("status " + r.status);
        return r.json();
      }).then(function (data) {
        var lvl = (data.lvl || "").trim();
        if (!lvl) throw new Error("empty response");
        src.value = lvl; syncHighlight(); runCommand("run");
        status.textContent = "Drafted by AI — review every fact and its source before trusting it.";
      }).catch(function (e) {
        // No backend / key configured: hand over a ready-made prompt.
        var p = fallbackPrompt(text);
        if (navigator.clipboard) navigator.clipboard.writeText(p).then(function () {});
        status.innerHTML = "AI endpoint not available (" + e.message + "). A ready-made prompt was copied to your clipboard — paste it into Claude or any LLM, then paste the LVL back here. To enable one-click drafting, set <code>ANTHROPIC_API_KEY</code> on the Vercel deployment (see DEPLOY.md).";
      }).finally(function () { btn.disabled = false; });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    if (window.mermaid) {
      try { window.mermaid.initialize({ startOnLoad: false, theme: "dark", securityLevel: "loose", flowchart: { curve: "basis" } }); } catch (e) {}
    }
    // Build lesson pills.
    var bar = $("#lessons");
    LESSONS.forEach(function (l, i) {
      var b = document.createElement("button");
      b.className = "tab" + (i === 0 ? " active" : "");
      b.textContent = l.title; b.setAttribute("data-lesson", l.id);
      b.addEventListener("click", function () { loadLesson(l); });
      bar.appendChild(b);
    });
    src.addEventListener("input", function () { syncHighlight(); });
    src.addEventListener("scroll", syncScroll);
    src.addEventListener("keydown", function (e) {
      if (e.key === "Tab") { e.preventDefault(); var s = src.selectionStart, en = src.selectionEnd;
        src.value = src.value.slice(0, s) + "    " + src.value.slice(en); src.selectionStart = src.selectionEnd = s + 4; syncHighlight(); }
      if ((e.metaKey || e.ctrlKey) && e.key === "Enter") { e.preventDefault(); runCommand("run"); }
    });
    document.querySelectorAll("[data-cmd]").forEach(function (btn) {
      btn.addEventListener("click", function () { runCommand(btn.getAttribute("data-cmd"), btn.getAttribute("data-usepred")); });
    });
    initAI();
    loadLesson(LESSONS[0]);
  });
})();
