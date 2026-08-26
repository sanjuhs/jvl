---
name: jvl-encode
description: >-
  Convert a legal document (contract, judgment, complaint, charge sheet, statute
  excerpt) into a JVL — Jhana Verifiable Law — program: a deterministic,
  statically-checkable encoding of its parties, facts, evidence, claims, rules,
  and the questions to be decided, with every fact traced back to its source.
  Use when the user wants to formalise, check, or reason over a legal document —
  e.g. "turn this contract into JVL", "which element of this charge is unproven",
  "are these clauses contradictory", "what happens if we drop this exhibit".
---

# JVL Encode

Turn legal prose into a checkable JVL program, then run the compiler and present
the trace. You do the fuzzy reading; JVL does the exact logic. **You never decide
the case — you produce a sourced, checkable argument for a human to review.**

## When to use this skill

- "Encode this contract / judgment / complaint as JVL."
- "Which elements of this offence are actually proven?"
- "Do these clauses contradict each other?"
- "What changes if Exhibit P-7 is excluded?"
- Any request to formalise, statically check, or reason over a legal document.

## Workflow

1. **Read `llm/system-prompt.md` and `llm/extraction-guide.md`** in this repo for
   the rules and the five-pass method. Skim `docs/02-language-tour.md` for the
   syntax and `docs/03-grammar.md` for exact shapes.

2. **Extract in five passes:** parties → facts (with `source(...)` + `status`) →
   claims/evidence → rules → constraints/asserts. Follow the golden rules:
   - Every `fact`/`evidence` gets a real `source(...)`. No source → make it a
     `claim` or omit it.
   - Never inflate confidence beyond what the document states.
   - Do not fabricate elements to make a conclusion true; leave unsupported
     elements unstated (they evaluate to `UNKNOWN`).

3. **Write the program to a `.jvl` file.**

4. **Compile in a loop.** Run the reference compiler and iterate until clean:
   ```bash
   cd reference-impl && pip install -e .        # once
   jvl check --audit path/to/case.jvl           # errors, warnings, unsourced conclusions
   jvl assert  path/to/case.jvl                 # derivation trace for each question
   jvl discover path/to/case.jvl "Offence(x)"   # which elements are still missing
   jvl check-contradictions path/to/case.jvl    # internal conflicts
   jvl constraints path/to/case.jvl             # objective money/date/duration checks
   jvl simulate path/to/case.jvl --without ID   # counterfactual
   jvl fmt --write path/to/case.jvl             # canonicalise before saving
   jvl diff A.jvl B.jvl                          # what changed between two versions
   jvl equiv A.jvl B.jvl                         # do two documents mean the same thing?
   ```

5. **Present both the program and the compiler output**, and call out: which
   questions are met and to what standard, which elements are missing
   (`discover`), any contradictions, and any objective constraint violations.
   Add the standard caveat: this is a research encoding for human review, not
   legal advice or a verdict.

## Guardrails

- If you cannot source a fact, say so and downgrade it — do not invent a
  citation.
- If the law is genuinely open on a point, encode the structure and leave the
  proposition `UNKNOWN`; do not guess a resolution.
- Always end with the human-review caveat.

## Reference

Language tour: `docs/02-language-tour.md` · Semantics: `docs/04-semantics.md` ·
Grammar: `spec/grammar.ebnf` · Worked examples: `examples/`.
