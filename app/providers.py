"""Answer-generation providers behind one small interface, so the same retrieval and honesty
rules can be run with different models (Stage 7d).

Each provider turns the OpenAI-style messages from build_messages() into its own API call and
returns the model's raw text (expected to be the JSON reply). Retrieval, citation checks and
scoring stay identical, so a comparison measures the model, not the plumbing.

Anthropic and Gemini are called over plain HTTPS (stdlib only): no extra SDKs to install, and
the request each one receives is visible here.

Amazon Bedrock (Stage 10b) is the exception: it uses boto3 (pure Python, dev-only), because AWS requests
must be signed with your AWS credentials (Signature V4), and boto3 also handles `aws sso login` sessions,
so no long-lived AWS keys are stored anywhere. One Bedrock provider class serves any Bedrock model through
the Converse API (one request shape for every model): Claude Haiku 4.5 and Amazon Nova 2 Lite here.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field

DEFAULT_ANTHROPIC_MODEL = "claude-haiku-4-5"
DEFAULT_GEMINI_MODEL = "gemini-3.5-flash"
GEMINI_THINKING_ALLOWANCE = 2048      # Gemini's output budget can include "thinking" tokens
RETRY_STATUSES = {429, 500, 502, 503, 504, 529}
DEFAULT_AWS_REGION = "eu-west-1"                                  # Ireland
DEFAULT_BEDROCK_CLAUDE = "eu.anthropic.claude-haiku-4-5-20251001-v1:0"   # EU cross-region inference profile
DEFAULT_BEDROCK_NOVA = "eu.amazon.nova-2-lite-v1:0"


class ProviderError(RuntimeError):
    pass


@dataclass
class Usage:
    """Tokens and time for the last call, for the comparison report."""
    input_tokens: int = 0
    output_tokens: int = 0
    seconds: float = 0.0


REQUEST_TIMEOUT = 45                  # seconds per attempt


def post_json(url, payload, headers, timeout=REQUEST_TIMEOUT):
    """POST JSON, return (status, parsed body or {})."""
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), method="POST",
                                 headers={"Content-Type": "application/json", **headers})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        try:
            return err.code, json.loads(err.read().decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return err.code, {}


def _say(msg):
    print(msg, file=sys.stderr, flush=True)


def post_with_retries(poster, url, payload, headers, attempts=4, sleep=time.sleep, log=_say):
    """Retry rate limits and transient server errors with backoff, saying so, so a wait never looks like a hang.

    Network failures (timeouts, DNS, refused connections) are retried the same way and raised on the last attempt.
    """
    host = url.split("/")[2] if "://" in url else url
    for attempt in range(attempts):
        last = attempt == attempts - 1
        try:
            status, body = poster(url, payload, headers)
        except (urllib.error.URLError, TimeoutError, OSError) as err:
            if last:
                raise ProviderError(f"{host}: no response ({err})") from None
            status, body, reason = None, {}, f"no response ({err})"
        else:
            if status not in RETRY_STATUSES or last:
                return status, body
            reason = f"HTTP {status}: {_error_text(body)[:120]}"
        wait = min(2 ** attempt * 2, 20)
        log(f"  {host}: {reason}; retrying in {wait}s ({attempt + 2}/{attempts})")
        sleep(wait)
    return status, body                                   # pragma: no cover


def split_messages(messages):
    """OpenAI-style messages -> (system text, list of user/assistant messages)."""
    system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
    rest = [m for m in messages if m["role"] != "system"]
    return system, rest


def _error_text(body):
    err = (body or {}).get("error")
    if isinstance(err, dict):
        return err.get("message") or json.dumps(err)[:200]
    return str(err or body)[:200]


@dataclass
class AzureOpenAIProvider:
    """Azure OpenAI chat deployment via the openai package (the live app's provider)."""
    client: object
    model: str
    name: str = "azure-openai"
    usage: Usage = field(default_factory=Usage)

    def generate(self, messages, max_tokens=400):
        start = time.time()
        resp = self.client.chat.completions.create(
            model=self.model, messages=messages, temperature=0,
            max_completion_tokens=max_tokens, response_format={"type": "json_object"})
        u = getattr(resp, "usage", None)
        self.usage = Usage(getattr(u, "prompt_tokens", 0) or 0, getattr(u, "completion_tokens", 0) or 0,
                           time.time() - start)
        return resp.choices[0].message.content


@dataclass
class AnthropicProvider:
    """Claude via the Messages API. No JSON mode: the prompt asks for JSON and the parser tolerates stray text."""
    api_key: str
    model: str = DEFAULT_ANTHROPIC_MODEL
    name: str = "anthropic"
    poster: object = post_json
    attempts: int = 4
    usage: Usage = field(default_factory=Usage)
    url: str = "https://api.anthropic.com/v1/messages"

    def generate(self, messages, max_tokens=400):
        system, rest = split_messages(messages)
        payload = {"model": self.model, "max_tokens": max_tokens, "temperature": 0,
                   "system": system, "messages": [{"role": m["role"], "content": m["content"]} for m in rest]}
        headers = {"x-api-key": self.api_key, "anthropic-version": "2023-06-01"}
        start = time.time()
        status, body = post_with_retries(self.poster, self.url, payload, headers, attempts=self.attempts)
        if status != 200:
            raise ProviderError(f"Anthropic HTTP {status}: {_error_text(body)}")
        u = body.get("usage") or {}
        self.usage = Usage(u.get("input_tokens", 0), u.get("output_tokens", 0), time.time() - start)
        return "".join(part.get("text", "") for part in body.get("content", []) if part.get("type") == "text")


@dataclass
class GeminiProvider:
    """Gemini via generateContent, with JSON output requested."""
    api_key: str
    model: str = DEFAULT_GEMINI_MODEL
    name: str = "gemini"
    poster: object = post_json
    attempts: int = 4
    usage: Usage = field(default_factory=Usage)
    base_url: str = "https://generativelanguage.googleapis.com/v1beta/models"

    def generate(self, messages, max_tokens=400):
        system, rest = split_messages(messages)
        payload = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]}
                         for m in rest],
            "generationConfig": {"temperature": 0, "maxOutputTokens": max_tokens + GEMINI_THINKING_ALLOWANCE,
                                 "responseMimeType": "application/json"},
        }
        headers = {"x-goog-api-key": self.api_key}
        start = time.time()
        status, body = post_with_retries(self.poster, f"{self.base_url}/{self.model}:generateContent", payload,
                                         headers, attempts=self.attempts)
        if status != 200:
            raise ProviderError(f"Gemini HTTP {status}: {_error_text(body)}")
        candidates = body.get("candidates") or []
        if not candidates:
            reason = (body.get("promptFeedback") or {}).get("blockReason", "no candidates")
            raise ProviderError(f"Gemini returned no answer ({reason})")
        parts = (candidates[0].get("content") or {}).get("parts") or []
        m = body.get("usageMetadata") or {}
        self.usage = Usage(m.get("promptTokenCount", 0),
                           m.get("candidatesTokenCount", 0) + m.get("thoughtsTokenCount", 0), time.time() - start)
        return "".join(p.get("text", "") for p in parts if not p.get("thought"))


BEDROCK_HINTS = {
    "AccessDeniedException": "your AWS role isn't allowed to call this model (check the IAM policy and that "
                             "model access is enabled in the Bedrock console)",
    "ValidationException": "the model ID or request was rejected (check the inference profile ID for your region)",
    "ResourceNotFoundException": "model not available to this account (for Anthropic models: submit the use-case form in the Bedrock console; else check the ID and AWS_REGION)",
    "ExpiredTokenException": "your AWS sign-in has expired: run  aws sso login --profile <your profile>",
    "UnrecognizedClientException": "AWS doesn't recognise these credentials: run  aws sso login",
}


@dataclass
class BedrockProvider:
    """Any Amazon Bedrock model via the Converse API (boto3). No JSON mode: like Claude direct, the prompt asks
    for JSON and the parser tolerates stray text. Retries and timeouts are set on the boto3 client."""
    client: object
    model: str
    name: str = "bedrock"
    usage: Usage = field(default_factory=Usage)

    def generate(self, messages, max_tokens=400):
        system, rest = split_messages(messages)
        start = time.time()
        try:
            resp = self.client.converse(
                modelId=self.model,
                system=[{"text": system}] if system else [],
                messages=[{"role": m["role"], "content": [{"text": m["content"]}]} for m in rest],
                inferenceConfig={"maxTokens": max_tokens, "temperature": 0})
        except Exception as err:                       # botocore errors: give a readable reason, never a key
            code = getattr(err, "response", {}).get("Error", {}).get("Code", type(err).__name__)
            hint = BEDROCK_HINTS.get(code, "")
            if type(err).__name__ in ("NoCredentialsError", "SSOTokenLoadError", "UnauthorizedSSOTokenError"):
                hint = "no AWS sign-in found: run  aws sso login --profile <your profile>  and set AWS_PROFILE in .env"
            detail = getattr(err, "response", {}).get("Error", {}).get("Message") or str(err)
            raise ProviderError(f"Bedrock {code}: {hint + ' | AWS says: ' if hint else ''}{detail[:300]}") from None
        u = resp.get("usage") or {}
        self.usage = Usage(u.get("inputTokens", 0), u.get("outputTokens", 0), time.time() - start)
        content = ((resp.get("output") or {}).get("message") or {}).get("content") or []
        text = "".join(part.get("text", "") for part in content)
        if not text:
            raise ProviderError(f"Bedrock returned no text (stopReason: {resp.get('stopReason')})")
        return text


def bedrock_client(env=None):
    """A bedrock-runtime client from your AWS profile (aws sso login), 45 s read timeout, 4 attempts."""
    env = os.environ if env is None else env
    try:
        import boto3
        from botocore.config import Config
    except ImportError:
        raise ProviderError("boto3 is not installed: pip install -r requirements-dev.txt") from None
    session = boto3.Session(profile_name=env.get("AWS_PROFILE") or None,
                            region_name=env.get("AWS_REGION") or DEFAULT_AWS_REGION)
    return session.client("bedrock-runtime", config=Config(read_timeout=REQUEST_TIMEOUT, connect_timeout=10,
                                                            retries={"total_max_attempts": 4, "mode": "standard"}))


PROVIDER_NAMES = ("azure-openai", "anthropic", "gemini", "bedrock-claude", "bedrock-nova")


def provider_from_env(name, azure_client=None, env=None, bedrock=None):
    """Build a provider by name from environment settings, or raise ProviderError saying what's missing."""
    env = os.environ if env is None else env
    if name == "azure-openai":
        if azure_client is None:
            from app.answering import azure_chat_client
            azure_client = azure_chat_client()
        return AzureOpenAIProvider(azure_client, env["AZURE_OPENAI_CHAT_DEPLOYMENT"])
    if name == "anthropic":
        if not env.get("ANTHROPIC_API_KEY"):
            raise ProviderError("ANTHROPIC_API_KEY is not set in .env")
        return AnthropicProvider(env["ANTHROPIC_API_KEY"], env.get("ANTHROPIC_MODEL") or DEFAULT_ANTHROPIC_MODEL)
    if name == "gemini":
        if not env.get("GEMINI_API_KEY"):
            raise ProviderError("GEMINI_API_KEY is not set in .env")
        return GeminiProvider(env["GEMINI_API_KEY"], env.get("GEMINI_MODEL") or DEFAULT_GEMINI_MODEL)
    if name in ("bedrock-claude", "bedrock-nova"):
        key, default = (("BEDROCK_CLAUDE_MODEL", DEFAULT_BEDROCK_CLAUDE) if name == "bedrock-claude"
                        else ("BEDROCK_NOVA_MODEL", DEFAULT_BEDROCK_NOVA))
        client = bedrock_client(env) if bedrock is None else bedrock
        return BedrockProvider(client, env.get(key) or default, name=name)
    raise ProviderError(f"unknown provider {name!r}; choose from {', '.join(PROVIDER_NAMES)}")
