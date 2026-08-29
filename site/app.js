/* LVL website interactions: syntax highlighting, tabs, nav, theme, copy. */
(function () {
  "use strict";

  // ---- LVL syntax highlighter -------------------------------------------
  var KEYWORDS = /^(jurisdiction|party|fact|evidence|claim|rule|obligation|permission|prohibition|constraint|exclusive|assert|prove|refute|explain|discover|requires|established_if|normally|except|unless|when|supports|refutes|asserts|by|from|source|status|under|for|and|or)\b/;
  var STATUS = /^(Established|Admitted|Alleged|Disputed|Refuted|Unknown|Proven|Supported|BalanceOfProbabilities|ClearAndConvincing|BeyondReasonableDoubt)\b/;
  var CURRENCY = /^(INR|USD|EUR|GBP|JPY|AUD|CAD|SGD|CNY|CHF)\s+[\d_]+/;

  function esc(s) {
    return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }
  function span(cls, txt) { return '<span class="' + cls + '">' + esc(txt) + "</span>"; }

  function highlightLVL(code) {
    var out = "", i = 0, n = code.length;
    while (i < n) {
      var rest = code.slice(i), m;
      // comment
      if ((m = /^(#|\/\/)[^\n]*/.exec(rest))) { out += span("tok-comment", m[0]); i += m[0].length; continue; }
      // string
      if ((m = /^"(?:[^"\\]|\\.)*"/.exec(rest))) { out += span("tok-str", m[0]); i += m[0].length; continue; }
      // money (currency + number)
      if ((m = CURRENCY.exec(rest))) { out += span("tok-num", m[0]); i += m[0].length; continue; }
      // date
      if ((m = /^\d{4}-\d{2}-\d{2}\b/.exec(rest))) { out += span("tok-num", m[0]); i += m[0].length; continue; }
      // number
      if ((m = /^\d[\d_]*(\.\d+)?\b/.exec(rest))) { out += span("tok-num", m[0]); i += m[0].length; continue; }
      // keyword
      if ((m = KEYWORDS.exec(rest))) { out += span("tok-key", m[0]); i += m[0].length; continue; }
      // status / standard
      if ((m = STATUS.exec(rest))) { out += span("tok-status", m[0]); i += m[0].length; continue; }
      // UpperCamel predicate / type
      if ((m = /^[A-Z][A-Za-z0-9_]*(\.[A-Za-z0-9_]+)*/.exec(rest))) { out += span("tok-pred", m[0]); i += m[0].length; continue; }
      // operators / punctuation
      if ((m = /^(<=|>=|==|!=|[{}()<>=:,])/.exec(rest))) { out += span("tok-op", m[0]); i += m[0].length; continue; }
      // default: single char
      out += esc(code[i]); i += 1;
    }
    return out;
  }

  function colorizeTerm(text) {
    return text.split("\n").map(function (line) {
      var l = esc(line);
      if (/^\s*⚖/.test(line)) return span("o-head", line);
      if (/RESULT:/.test(line) || /≟|→/.test(line)) l = l.replace(/(SUPPORTED|PROVEN|ESTABLISHED)/g, '<span class="o-ok">$1</span>').replace(/(UNKNOWN|UNSUPPORTED)/g, '<span class="o-dim">$1</span>').replace(/(REFUTED|DISPUTED)/g, '<span class="o-warn">$1</span>');
      if (/[✓]|EQUIVALENT|meets|holds/.test(line)) return '<span class="o-ok">' + l + "</span>";
      if (/[✗⚠]|VIOLATED|DIFFERENT|does not|FAILED/.test(line)) return '<span class="o-bad">' + l + "</span>";
      // dotted-leader status lines
      l = l.replace(/\b(ESTABLISHED|PROVEN|SUPPORTED)\b/g, '<span class="o-ok">$1</span>')
           .replace(/\b(UNKNOWN|UNSUPPORTED)\b/g, '<span class="o-dim">$1</span>')
           .replace(/\b(DISPUTED|REFUTED)\b/g, '<span class="o-warn">$1</span>')
           .replace(/(→\s+[^\n<]+)/g, '<span class="o-dim">$1</span>');
      return l;
    }).join("\n");
  }

  function render() {
    document.querySelectorAll("pre code.lvl").forEach(function (el) {
      el.innerHTML = highlightLVL(el.textContent);
    });
    document.querySelectorAll("pre code.term").forEach(function (el) {
      el.innerHTML = colorizeTerm(el.textContent);
    });
  }

  // ---- tabs --------------------------------------------------------------
  function initTabs() {
    document.querySelectorAll("[data-tabs]").forEach(function (group) {
      var tabs = group.querySelectorAll(".tab");
      var panelSel = group.getAttribute("data-tabs");
      var panels = document.querySelectorAll(panelSel);
      tabs.forEach(function (tab) {
        tab.addEventListener("click", function () {
          tabs.forEach(function (t) { t.classList.remove("active"); });
          tab.classList.add("active");
          var key = tab.getAttribute("data-tab");
          panels.forEach(function (p) {
            p.style.display = p.getAttribute("data-panel") === key ? "" : "none";
          });
        });
      });
    });
  }

  // ---- nav toggle + theme + copy ----------------------------------------
  function initNav() {
    var toggle = document.querySelector(".nav-toggle");
    var links = document.querySelector(".nav .links");
    if (toggle && links) toggle.addEventListener("click", function () { links.classList.toggle("open"); });
  }
  function initTheme() {
    var btn = document.querySelector("[data-theme-toggle]");
    var saved = null;
    try { saved = localStorage.getItem("lvl-theme"); } catch (e) {}
    if (saved) document.documentElement.setAttribute("data-theme", saved);
    if (btn) btn.addEventListener("click", function () {
      var cur = document.documentElement.getAttribute("data-theme") === "light" ? "" : "light";
      if (cur) document.documentElement.setAttribute("data-theme", cur);
      else document.documentElement.removeAttribute("data-theme");
      try { localStorage.setItem("lvl-theme", cur); } catch (e) {}
    });
  }
  function initCopy() {
    document.querySelectorAll(".copy-btn").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var pre = btn.closest(".window").querySelector("pre");
        navigator.clipboard.writeText(pre.textContent).then(function () {
          var old = btn.textContent; btn.textContent = "copied ✓";
          setTimeout(function () { btn.textContent = old; }, 1400);
        });
      });
    });
  }

  // Expose the highlighters so the interactive editor can reuse them.
  window.LVLHL = { highlightLVL: highlightLVL, colorizeTerm: colorizeTerm, esc: esc };

  document.addEventListener("DOMContentLoaded", function () {
    render(); initTabs(); initNav(); initTheme(); initCopy();
  });
})();
