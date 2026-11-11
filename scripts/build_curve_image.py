"""Build app/static/curve-og.png (ASK-75): the evidence curve as a 1200x627 link-preview image.

LinkedIn, WhatsApp and Slack show this image when someone shares /curve, and it is the picture on the LinkedIn
Featured item. It is drawn from the same capability.json and profile/curve.yaml as the page, by photographing
the /curve/card route in a headless browser.

    python -m scripts.build_curve_image                       # from the live capability data (CAPABILITY_SOURCE)
    python -m scripts.build_curve_image --capability data/capability.json --out /tmp/curve.png

Needs Playwright with Chromium (pip install playwright && playwright install chromium); it is a dev-only tool.
Rebuild it when a dot changes tier, commit the PNG, and re-add the Featured link: LinkedIn caches previews.
"""
import argparse
import json
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "app" / "static" / "curve-og.png"
LIVE = "https://raw.githubusercontent.com/BBSISK/ask-barry/capability-data/data/capability.json"


def card_html(capability):
    """The /curve/card page for this capability data, rendered without a server."""
    from app import create_app
    from app.capability.store import CapabilityStore
    app = create_app("testing", capability_store=CapabilityStore(source="unused", fetch=lambda _s: capability))
    resp = app.test_client().get("/curve/card")
    if resp.status_code != 200:
        sys.exit(f"/curve/card answered {resp.status_code}: {resp.get_data(as_text=True)}")
    return resp.get_data(as_text=True)


def photograph(html, out):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1200, "height": 627}, device_scale_factor=1)
        page.set_content(html, wait_until="load")
        page.screenshot(path=str(out), clip={"x": 0, "y": 0, "width": 1200, "height": 627})
        browser.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Build the evidence curve preview image")
    parser.add_argument("--capability", default=LIVE, help="capability.json path or https URL (default: the live data)")
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    args = parser.parse_args(argv)
    from app.capability.store import _fetch, problems
    capability = _fetch(args.capability)
    if not capability or problems(capability):
        sys.exit(f"{args.capability} isn't a valid capability.json")
    photograph(card_html(capability), args.out)
    print(f"Wrote {args.out} (evidence as of {capability['generated_at'][:10]})")


if __name__ == "__main__":
    main()
