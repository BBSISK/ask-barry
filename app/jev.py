"""Stage 9: TypeSafe Jev, a "decision model", via Cloudflare Workers AI.

Jev doesn't write text: it answers typed questions about a piece of content (the "state") and returns
structured answers with probabilities:
  noul   yes/no            -> {"noul": 0.93}                  (probability of "true")
  choice pick one option   -> {"choice": "x", "confidence": ..}
  score  ordered levels    -> {"score": 1.04, "confidence": ..}

Stage 9a uses it as a second, independent judge in the evaluations (a different kind of model from the
gpt-4.1-mini judge). Only public documentation and generated answers are sent; the model is listed on
Cloudflare with zero data retention. Stdlib HTTP only, like app/providers.py.
"""
import os

from app.providers import ProviderError, post_json, post_with_retries

MODEL = "typesafe/jev"
URL = "https://api.cloudflare.com/client/v4/accounts/{account}/ai/run"
SETTINGS = ("CLOUDFLARE_ACCOUNT_ID", "CLOUDFLARE_API_TOKEN")


def configured(env=None):
    env = os.environ if env is None else env
    return all(env.get(name, "").strip() for name in SETTINGS)


def noul(instructions, true=None, false=None):
    q = {"type": "noul", "instructions": instructions}
    if true or false:
        q["criteria"] = {"true": true or "Yes", "false": false or "No"}
    return q


def choice(instructions, options):
    return {"type": "choice", "instructions": instructions, "criteria": dict(options)}


def score(instructions, levels):
    return {"type": "score", "instructions": instructions, "criteria": list(levels)}


class JevClient:
    def __init__(self, account_id, api_token, poster=post_json, attempts=4):
        self.url = URL.format(account=account_id)
        self.headers = {"Authorization": f"Bearer {api_token}"}
        self.poster, self.attempts = poster, attempts
        self.usage = {}

    def ask(self, state, questions):
        """state: str or JSON-able object; questions: {key: noul()/choice()/score()} -> {key: answer dict}."""
        payload = {"model": MODEL, "input": {"state": state, "questions": questions}}
        status, body = post_with_retries(self.poster, self.url, payload, self.headers, attempts=self.attempts)
        if status != 200:
            errors = (body or {}).get("errors") or body
            raise ProviderError(f"Jev (Cloudflare) HTTP {status}: {str(errors)[:200]}")
        result = body if isinstance(body, dict) else {}
        for _ in range(3):              # Cloudflare wraps it: {"result": {"state": "Completed", "result": {...}}}
            if "answers" in result or not isinstance(result.get("result"), dict):
                break
            result = result["result"]
        answers = result.get("answers")
        if not isinstance(answers, dict) or set(answers) != set(questions):
            raise ProviderError(f"Jev returned unexpected answers: {str(result)[:200]}")
        self.usage = result.get("usage", {})
        self.model_version = result.get("model", MODEL)
        return answers


def client_from_env():
    if not configured():
        raise ProviderError("Missing CLOUDFLARE_ACCOUNT_ID / CLOUDFLARE_API_TOKEN in .env")
    return JevClient(os.environ["CLOUDFLARE_ACCOUNT_ID"].strip(), os.environ["CLOUDFLARE_API_TOKEN"].strip())
