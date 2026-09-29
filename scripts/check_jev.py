"""Check access to TypeSafe Jev on Cloudflare Workers AI (Stage 9).

    python -m scripts.check_jev        # needs CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN in .env

Asks Jev two questions it should answer oppositely, about a sentence from Barry's public docs.
"""
import sys
import time

SOURCE = "Wall Inspector runs as a full-stack application with Docker Compose, including PostgreSQL 15."


def main():
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    from app.jev import client_from_env, noul
    from app.providers import ProviderError
    try:
        client = client_from_env()
        start = time.time()
        answers = client.ask({"context": "Wall Inspector is a software project that Barry Sisk built.",
                              "source": SOURCE,
                              "claims": {"a": "Barry has used Docker.", "b": "Barry has deployed Kubernetes clusters."}}, {
            "a_supported": noul("Using `context` and `source` only, is claim `claims.a` supported?",
                                true="The context and source together show the claim", false="They don't show it"),
            "b_supported": noul("Using `context` and `source` only, is claim `claims.b` supported?",
                                true="The context and source together show the claim", false="They don't show it"),
        })
    except ProviderError as err:
        sys.exit(f"FAIL: {err}")
    a, b = answers["a_supported"]["noul"], answers["b_supported"]["noul"]
    print(f"model {client.model_version} · {time.time() - start:.1f}s · usage {client.usage}")
    print(f"  Docker claim supported?      p={a:.2f}  (expect high)")
    print(f"  Kubernetes claim supported?  p={b:.2f}  (expect low)")
    print("PASS" if a > 0.5 > b else "CHECK: answers not as expected")


if __name__ == "__main__":
    main()
