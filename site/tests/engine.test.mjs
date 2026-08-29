/* Parity + smoke tests for the in-browser JS engine.
   Run: node site/tests/engine.test.mjs
   Verifies the JS port reproduces the key results of the Python reference. */

import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "..", "..");

// Load the engine into a sandbox with a fake `window`.
const src = fs.readFileSync(path.join(here, "..", "lvl-engine.js"), "utf8");
const sandbox = { window: {}, JSON, Math, console };
vm.createContext(sandbox);
vm.runInContext(src, sandbox);
const LVL = sandbox.window.LVL;

let pass = 0, fail = 0;
function check(name, cond) {
  if (cond) { pass++; console.log("  ✓ " + name); }
  else { fail++; console.log("  ✗ " + name); }
}
function ex(n) { return fs.readFileSync(path.join(root, "examples", n), "utf8"); }

console.log("JS engine parity tests\n");

// Example 01 — loan
let r = LVL.run(ex("01-loan-vs-investment.lvl"), "assert");
check("01 loan assert prints SUPPORTED", /Loan\(transfer_17\).*SUPPORTED/s.test(r.text));
check("01 transfer is ESTABLISHED", /TransferOfValue\(transfer_17\).*ESTABLISHED/s.test(r.text));
check("01 provenance shown", /BankStatement_3 p\.2 ¶4/.test(r.text));
check("01 meets balance of probabilities", /meets BalanceOfProbabilities/.test(r.text));

// Example 03 — criminal
r = LVL.run(ex("03-cheating-s420.lvl"), "discover", "Cheating(payment)");
check("03 discover finds mental element", /DishonestIntentionAtInception\(payment\) — UNKNOWN/.test(r.text));
r = LVL.run(ex("03-cheating-s420.lvl"), "assert");
check("03 fails beyond reasonable doubt", /does not meet BeyondReasonableDoubt/.test(r.text));
r = LVL.run(ex("03-cheating-s420.lvl"), "contradictions");
check("03 contradiction detected", /PresentAtMeeting/.test(r.text));

// Example 02 — constraints
r = LVL.run(ex("02-nda-contract.lvl"), "constraints");
check("02 damages_within_cap VIOLATED", /damages_within_cap: VIOLATED/.test(r.text));
check("02 disclosure_before_expiry holds", /disclosure_before_expiry: holds/.test(r.text));

// Example 05 — default logic
r = LVL.run(ex("05-limitation-default.lvl"), "assert");
check("05 default is rebutted (TimeBarred REFUTED)", /TimeBarred\(claim1\).*REFUTED/s.test(r.text));

// emit
r = LVL.run(ex("01-loan-vs-investment.lvl"), "emit");
try {
  const data = JSON.parse(r.text);
  const props = Object.fromEntries(data.atoms.map(a => [a.proposition, a.status]));
  check("emit produces valid JSON with atoms", props["Loan(transfer_17)"] === "SUPPORTED");
} catch (e) { check("emit produces valid JSON with atoms", false); }

// check command
r = LVL.run("fact f : Thing { a: 1 }\nassert Thing(f)", "check");
check("check warns on missing provenance", /provenance/.test(r.text));
r = LVL.run('claim c by Ghost : "x" asserts P(a)', "check");
check("check errors on undeclared party", /undeclared party/.test(r.text) && r.ok === false);

// parse error handling
r = LVL.run("party A Person", "check");
check("parse error is reported gracefully", /error/.test(r.text) && r.ok === false);

console.log("\n" + pass + " passed, " + fail + " failed");
process.exit(fail ? 1 : 0);
