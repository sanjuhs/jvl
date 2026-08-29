"""Natural-language front-end: map an English question to an LVL query.

This is the ``lvl ask`` path. The division of labour is the project's whole
thesis: the LLM does **only** the translation (English question -> a single LVL
query line), and the deterministic engine computes the actual answer. The model
never decides whether a proposition holds — it just picks which query to run.

Uses the standard library only (``urllib``) so the reference implementation
keeps its zero-dependency promise. Requires ``ANTHROPIC_API_KEY`` in the
environment; the model is configurable via ``LVL_ASSIST_MODEL``.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

_ENDPOINT = "https://api.anthropic.com/v1/messages"

_SYSTEM = """You translate a plain-English question about an LVL (Legal Verifiable
Language) program into exactly ONE LVL query line. You never answer the question
yourself — the compiler does that. Output ONLY the query line, nothing else.

Valid query forms:
  assert Pred(args) under BalanceOfProbabilities      (or BeyondReasonableDoubt)
  explain Pred(args)
  discover Pred(args)
  refute Pred(args)

Use predicate and entity names that appear in the program. Choose:
  - assert  for "does X hold / is X liable / is the offence made out"
  - discover for "what is missing / what else is needed for X"
  - explain for "why / how is X established / show the reasoning"
Pick the standard from context (criminal charge -> BeyondReasonableDoubt,
otherwise BalanceOfProbabilities)."""


class NLError(RuntimeError):
    pass


def question_to_query(program_src: str, question: str) -> str:
    """Return a single LVL query line for ``question`` over ``program_src``."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise NLError(
            "ANTHROPIC_API_KEY is not set. `lvl ask` needs it to translate the "
            "question into a query. Export it, or write the query yourself with "
            "`lvl assert/explain/discover`.")
    model = os.environ.get("LVL_ASSIST_MODEL", "claude-sonnet-5")
    body = {
        "model": model,
        "max_tokens": 200,
        "system": _SYSTEM,
        "messages": [{
            "role": "user",
            "content": f"LVL program:\n\n{program_src}\n\nQuestion: {question}\n\n"
                       f"Output the single LVL query line now.",
        }],
    }
    req = urllib.request.Request(
        _ENDPOINT,
        data=json.dumps(body).encode(),
        headers={
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raise NLError(f"Anthropic API error {e.code}: {e.read().decode()[:300]}") from e
    except urllib.error.URLError as e:
        raise NLError(f"network error: {e}") from e

    text = "".join(b.get("text", "") for b in data.get("content", [])
                   if b.get("type") == "text").strip()
    # Strip fences/backticks if the model added them.
    text = text.strip("`").strip()
    if text.lower().startswith("lvl"):
        text = text[3:].strip()
    line = next((ln.strip() for ln in text.splitlines() if ln.strip()), "")
    if not line:
        raise NLError("the model returned an empty query")
    return line
