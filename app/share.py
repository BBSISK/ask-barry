"""Stage 8f: share an evidence map on the spot (QR code on screen, WhatsApp, email, copy link).

A share link carries the evidence map itself: compressed JSON, signed with the server's SECRET_KEY
(HMAC-SHA256). So links keep working for weeks without a database, and nobody can edit one to make it
claim evidence the agent didn't verify: a changed link fails the signature check and isn't shown.
The job ad itself is never in the link, only the requirements and the evidence found for them.

Share links are long, which is fine for WhatsApp and email but too dense for a QR code on a phone screen,
so the on-screen QR uses a short /s/<job id> link that redirects to the signed one while the job is in memory.
"""
import base64
import binascii
import hashlib
import hmac
import io
import json
import time
import zlib

VERSION = 1
SIG_BYTES = 16
ROW_FIELDS = ("requirement", "kind", "status", "evidence", "sources", "notes")


class BadShareLink(ValueError):
    pass


def slim(report):
    """Only what the shared page shows (from Report.to_dict())."""
    return {"role_title": report.get("role_title", ""), "counts": report.get("counts", {}),
            "dropped": report.get("dropped", []), "fallback": bool(report.get("fallback")),
            "requirements": [{k: row.get(k) for k in ROW_FIELDS} for row in report.get("requirements", [])]}


def _key(secret):
    return hashlib.sha256(b"ask-barry-share-v1:" + str(secret).encode()).digest()


def pack(report, secret, now=None):
    data = {"v": VERSION, "t": int(now if now is not None else time.time()), "r": slim(report)}
    raw = zlib.compress(json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode(), 9)
    sig = hmac.new(_key(secret), raw, hashlib.sha256).digest()[:SIG_BYTES]
    return base64.urlsafe_b64encode(sig + raw).decode().rstrip("=")


def unpack(token, secret):
    """Token -> {"created": epoch seconds, "report": {...}}. Raises BadShareLink if invalid or altered."""
    try:
        blob = base64.urlsafe_b64decode(token + "=" * (-len(token) % 4))
    except (binascii.Error, ValueError):
        raise BadShareLink("not a share link") from None
    sig, raw = blob[:SIG_BYTES], blob[SIG_BYTES:]
    if len(sig) < SIG_BYTES or not hmac.compare_digest(sig, hmac.new(_key(secret), raw, hashlib.sha256).digest()[:SIG_BYTES]):
        raise BadShareLink("signature check failed")
    try:
        data = json.loads(zlib.decompress(raw, bufsize=65536).decode())
    except (zlib.error, ValueError):
        raise BadShareLink("unreadable") from None
    if data.get("v") != VERSION:
        raise BadShareLink("unsupported version")
    return {"created": data.get("t", 0), "report": data.get("r", {})}


def qr_data_uri(url):
    """A QR code as an inline SVG data URI (pure Python: no image library needed on the server)."""
    import qrcode
    import qrcode.image.svg
    img = qrcode.make(url, image_factory=qrcode.image.svg.SvgPathFillImage, border=2)
    buf = io.BytesIO()
    img.save(buf)
    return "data:image/svg+xml;base64," + base64.b64encode(buf.getvalue()).decode()
