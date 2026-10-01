"""Stage 9a: two judges for one question: "is this claim supported by these sources?"

  - LLM judge: the gpt-4.1-mini deployment (the same model family that writes the answers), JSON yes/no.
  - Jev judge: TypeSafe's decision model via Cloudflare (a different kind of model), a probability.

Both see exactly the same state: the claim plus the sources as the answering model saw them (each labelled
with repo, file and section), because an unlabelled source makes true claims about Barry look unsupported
(learned in Stage 6 for the LLM judge and again on Jev's first call in Stage 9).
"""
import json
import re
import time

CONTEXT = ("The sources are Barry Sisk's public project documentation. Each is labelled [n] repo/file "
           "(section). A claim about Barry is supported when a source about one of his projects states it.")

LLM_RULES = CONTEXT + """
Decide whether the CLAIM is fully supported by the SOURCES. Paraphrase is fine; anything the sources don't
state (a detail, a number, a project, a planned thing described as done) makes it unsupported.
Reply with JSON only: {"supported": true or false}"""

JEV_INSTRUCTIONS = "Using only `sources` (and `context`), is `claim` fully supported?"
JEV_CRITERIA = {"true": "The sources state everything the claim says (paraphrase is fine)",
                "false": "Some part of the claim is not stated in the sources"}

_CITE = re.compile(r"\s*\[\d+\]")


def split_claims(answer_text, min_chars=25):
    """An answer -> its sentences (the unit we label and judge), citation markers removed."""
    text = _CITE.sub("", answer_text or "")
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p.strip() for p in parts if len(p.strip()) >= min_chars]


class LLMJudge:
    name = "gpt-4.1-mini judge"

    def __init__(self, provider):
        self.provider = provider

    def judge(self, claim, sources):
        start = time.time()
        raw = self.provider.generate([{"role": "system", "content": LLM_RULES},
                                      {"role": "user", "content": f"SOURCES:\n{sources}\n\nCLAIM: {claim}"}],
                                     max_tokens=30)
        try:
            supported = bool(json.loads(raw).get("supported"))
        except (TypeError, ValueError, AttributeError):
            supported = None
        usage = getattr(self.provider, "usage", None)
        return {"supported": supported, "p": None if supported is None else float(supported),
                "seconds": round(time.time() - start, 2), "input_tokens": getattr(usage, "input_tokens", 0)}


class JevJudge:
    name = "Jev"

    def __init__(self, client):
        self.client = client

    def judge(self, claim, sources):
        from app.jev import noul
        start = time.time()
        answers = self.client.ask({"context": CONTEXT, "sources": sources, "claim": claim},
                                  {"supported": noul(JEV_INSTRUCTIONS, **JEV_CRITERIA)})
        p = float(answers["supported"]["noul"])
        return {"supported": p >= 0.5, "p": p, "seconds": round(time.time() - start, 2),
                "input_tokens": (self.client.usage or {}).get("input_tokens", 0)}
