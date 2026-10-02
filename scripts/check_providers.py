"""Check which answer-generation providers are set up, with one tiny request each (fractions of a cent).

Usage:
    python -m scripts.check_providers                              # all providers
    python -m scripts.check_providers bedrock-claude bedrock-nova   # just these

Settings in .env (keys never printed):
    ANTHROPIC_API_KEY, optional ANTHROPIC_MODEL   (default claude-haiku-4-5)
    GEMINI_API_KEY,    optional GEMINI_MODEL      (default gemini-3.5-flash)
    Azure OpenAI uses the AZURE_* settings the app already has.
    Bedrock: sign in first with  aws sso login --profile <profile>; then AWS_PROFILE, optional AWS_REGION
    (default eu-west-1), BEDROCK_CLAUDE_MODEL, BEDROCK_NOVA_MODEL (EU inference profile IDs by default).
"""
import json
import sys

PING = [{"role": "system", "content": 'Reply with a JSON object only: {"ok": true, "model": "<your model name>"}'},
        {"role": "user", "content": "Ping."}]


def check(name, build, log=print):
    from app.providers import ProviderError
    try:
        provider = build(name)
        if hasattr(provider, "attempts"):
            provider.attempts = 1                 # a check should answer quickly, not wait through retries
        log(f"  {name:<13} checking {provider.model} ...")
        raw = provider.generate(PING, max_tokens=50)
    except (ProviderError, KeyError) as err:
        hint = " (is the model ID right? see the provider's models page)" if "404" in str(err) else ""
        log(f"  {name:<13} NOT READY  {err}{hint}")
        return False
    except Exception as err:                      # network etc.
        log(f"  {name:<13} ERROR      {type(err).__name__}: {err}")
        return False
    try:
        json.loads(raw[raw.index("{"): raw.rindex("}") + 1])
        shape = "JSON ok"
    except ValueError:
        shape = f"not JSON: {raw[:60]!r}"
    u = provider.usage
    log(f"  {name:<13} OK         {provider.model} · {shape} · {u.seconds:.1f}s · {u.input_tokens}/{u.output_tokens} tokens")
    return True


def main(argv=None):
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    from app.providers import PROVIDER_NAMES, provider_from_env
    names = (sys.argv[1:] if argv is None else argv) or list(PROVIDER_NAMES)
    unknown = [n for n in names if n not in PROVIDER_NAMES]
    if unknown:
        sys.exit(f"Unknown provider(s): {', '.join(unknown)}. Choose from: {', '.join(PROVIDER_NAMES)}")
    print("Answer-generation providers:")
    ready = [check(name, provider_from_env) for name in names]
    if not all(ready):
        sys.exit("\nFix the NOT READY lines above, then run this again.")
    print("\nAll providers ready.")


if __name__ == "__main__":
    main()
