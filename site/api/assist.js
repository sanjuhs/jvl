/* Vercel serverless function: draft a JVL program from a plain-English scenario.
 *
 * The ANTHROPIC_API_KEY stays server-side and is never exposed to the browser.
 * Model defaults to a fast one (the user's priority) and is overridable via the
 * JVL_ASSIST_MODEL env var — set it to claude-opus-5 for maximum quality.
 *
 * Uses raw HTTPS (global fetch, Node 18+) so the static site needs no build
 * step or npm dependencies.
 */

var SYSTEM = [
  "You are a JVL (Jhana Verifiable Law) extractor. Convert the user's legal scenario",
  "into a single, valid JVL program. JVL is a small DSL; here is all you need:",
  "",
  "- jurisdiction Dotted.Name",
  '- party ID = Person \"Label\"   (or Org)',
  "- fact ID : TypeName { field: value, ... } from source(doc=\"..\", page=N, para=N) status Established",
  "    statuses: Established | Admitted | Alleged | Disputed | Refuted",
  "    values: refs (A), money (INR 1_000_000), dates (2025-03-10), numbers, strings",
  "- evidence ID : TypeName { ... } from source(...) supports Pred(args)   (or refutes)",
  '- claim ID by PARTY : \"text\" asserts Pred(args)',
  "- rule ID: Head(t) requires A(t) B(t)          (conjunction)",
  "- rule ID: Head(t) established_if A(t) or B(t)  (disjunction)",
  "- rule ID: Head(t) normally A(t) except when E(t)   (defeasible default:",
  "    holds by default, but a holding exception rebuts it — use for 'normally",
  "    X unless Y' statute language)",
  "- exclusive { PredA(t) PredB(t) }",
  "- constraint ID: a.field <= b.field   (ops: <= >= < > == != before after)",
  "- constraint ID: a.date within 30 days after b.date   (durations: units",
  "    days/weeks/months/years; direction of/before/after)",
  "- assert Pred(args) under BalanceOfProbabilities   (or BeyondReasonableDoubt)",
  "",
  "RULES: every fact/evidence MUST have a from source(...). Never inflate confidence",
  "beyond what the scenario states. A party's contention is a claim, not a fact.",
  "Do NOT fabricate elements to make a conclusion true — leave unsupported elements",
  "unstated. Predicates are UpperCamelCase; entity ids are short snake_case;",
  "rule variables are lowercase (t, p). End with one or more assert lines under the",
  "correct standard (BeyondReasonableDoubt for criminal charges, else",
  "BalanceOfProbabilities).",
  "",
  "Whitespace is insignificant. Output ONLY a single ```jvl fenced code block."
].join("\n");

module.exports = async function (req, res) {
  res.setHeader("Content-Type", "application/json");
  if (req.method !== "POST") { res.status(405).json({ error: "POST only" }); return; }

  var key = process.env.ANTHROPIC_API_KEY;
  if (!key) { res.status(501).json({ error: "ANTHROPIC_API_KEY not configured on this deployment" }); return; }

  var body = req.body;
  try { if (typeof body === "string") body = JSON.parse(body || "{}"); } catch (e) { body = {}; }
  var prompt = ((body && body.prompt) || "").toString().slice(0, 8000).trim();
  if (!prompt) { res.status(400).json({ error: "empty prompt" }); return; }

  var model = process.env.JVL_ASSIST_MODEL || "claude-sonnet-5";
  try {
    var r = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: { "x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json" },
      body: JSON.stringify({
        model: model,
        max_tokens: 2000,
        system: SYSTEM,
        messages: [{ role: "user", content: "Scenario:\n" + prompt + "\n\nProduce the JVL program now." }]
      })
    });
    if (!r.ok) {
      var errText = await r.text();
      res.status(502).json({ error: "upstream " + r.status, detail: errText.slice(0, 400) });
      return;
    }
    var data = await r.json();
    var text = (data.content || []).filter(function (b) { return b.type === "text"; })
      .map(function (b) { return b.text; }).join("\n");
    var m = text.match(/```(?:jvl)?\s*([\s\S]*?)```/);
    var jvl = (m ? m[1] : text).trim();
    res.status(200).json({ jvl: jvl, model: model });
  } catch (e) {
    res.status(500).json({ error: "request failed", detail: String(e).slice(0, 300) });
  }
};
