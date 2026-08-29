# Teaching an LLM to write LVL

LVL is designed around a division of labour:

> **The LLM does the fuzzy part** — reading a messy legal document and drafting a
> structured program with honest sources. **LVL does the exact part** —
> deterministic, checkable logic the model is bad at.

This folder is a complete kit for making a language model reliably emit valid
LVL. It contains:

| File | Purpose |
|---|---|
| [`system-prompt.md`](system-prompt.md) | Drop-in system prompt: turns a model into an LVL extractor |
| [`extraction-guide.md`](extraction-guide.md) | The method: how to read a document and map it to LVL nodes |
| [`few-shot.md`](few-shot.md) | Input-document → LVL exemplars for in-context learning |
| [`claude-skill/SKILL.md`](claude-skill/SKILL.md) | A ready-to-use Claude / Claude Code skill |

## The loop that makes it reliable

An LLM writing LVL is not trusted blindly — it is put in a **compile loop**, and
this is the whole trick:

```
  document ──► LLM drafts .lvl ──► `lvl check` ──► errors? ──► LLM fixes ──► ...
                                        │
                                        ▼ clean
                                  `lvl assert` / `explain`
                                        │
                                        ▼
                              human reviews the trace
```

Because LVL is deterministic and the compiler's errors are precise, the model
gets a hard signal it can iterate against — unlike free-form legal prose, where
nothing tells it when it is wrong. The provenance requirement adds a second
signal: `lvl check` warns on any fact with no `source(...)`, so the model is
pushed to cite the document rather than invent.

## Why LVL is *designed* to be LLM-writable

Every syntax decision was made with a model's failure modes in mind:

- **Whitespace-insignificant** — no indentation to get subtly wrong.
- **Regular, keyword-led statements** — each line's job is obvious from its first
  word.
- **A tiny keyword set** — the whole language fits in the tour, so it fits in
  context.
- **Local structure** — a `fact` or `rule` is self-contained; the model never has
  to hold the whole file in mind to write one correct line.

## The golden rules for a model (short version)

1. **Cite everything.** Every `fact` and `evidence` gets a `source(...)` pointing
   at a real place in the document. No source, no fact.
2. **Never upgrade confidence.** If the document says "alleged", the status is
   `Alleged`, not `Established`. Map the document's own hedging faithfully.
3. **Claims are not facts.** A party's contention is a `claim`; only record
   evidence as `evidence`; only genuinely-accepted matters as `fact ... status
   Established`.
4. **Encode the logic you can, leave the rest open.** Write the rule structure
   ("the offence requires A ∧ B ∧ C"); do not fabricate the mental element —
   leave it `UNKNOWN` and let `discover` surface it.
5. **Compile before you answer.** Run `lvl check`, fix every error, and only then
   present the program and its trace.

The long version, with the mapping method and worked examples, is in
[`extraction-guide.md`](extraction-guide.md).
