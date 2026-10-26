"""Read capability.json for the page, the API and the MCP tool (ASK-42).

The nightly workflow builds the file and commits it to the capability-data branch (ASK-62). The live app reads it
from CAPABILITY_SOURCE, a local path or an https URL (in production the raw GitHub URL of the file on that branch),
so a nightly rebuild shows up without a redeploy. The result is cached for a few minutes. A broken or invalid file
never replaces the last good copy. If the URL can't be read before there is any good copy (say, just after a
restart while GitHub is down), the snapshot shipped with the app is used, dated by its own generated_at. A missing
file means "not generated yet", never an error page.
"""
import json
import logging
import time
import urllib.request
from pathlib import Path

from jsonschema import Draft202012Validator

from app.capability.pack import schema

log = logging.getLogger(__name__)
DEFAULT_SOURCE = str(Path(__file__).resolve().parents[2] / "data" / "capability.json")
TTL_SECONDS = 600


def _fetch(source, timeout=10):
    if source.startswith("https://"):
        req = urllib.request.Request(source, headers={"User-Agent": "ask-barry-capability"})
        # bandit B310 (urlopen scheme): https only (checked above)
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec B310
            return json.loads(resp.read().decode("utf-8"))
    path = Path(source)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def problems(data):
    """Schema problems in a capability document ([] when it's valid)."""
    return [f"{'/'.join(str(p) for p in e.path) or '(top)'}: {e.message}"
            for e in Draft202012Validator(schema("capability")).iter_errors(data)]


class CapabilityStore:
    def __init__(self, source=None, ttl=TTL_SECONDS, fetch=_fetch, clock=time.monotonic):
        self.source = source or DEFAULT_SOURCE
        self.ttl, self.fetch, self.clock = ttl, fetch, clock
        self._data, self._loaded = None, None

    def get(self):
        if self._loaded is not None and self.clock() - self._loaded < self.ttl:
            return self._data
        try:
            data = self.fetch(self.source)
        except Exception as err:                      # network down, bad JSON: keep what we had
            log.warning("capability: couldn't read %s (%s); keeping the last good copy", self.source, err)
            data = self._data
        else:
            if data is not None and problems(data):
                log.warning("capability: %s is invalid (%s); keeping the last good copy",
                            self.source, "; ".join(problems(data)[:3]))
                data = self._data
        if data is None and self.source != DEFAULT_SOURCE:
            data = self._snapshot()
        self._data, self._loaded = data, self.clock()
        return data

    def _snapshot(self):
        """The copy shipped with the app (main's data/capability.json), if it is valid."""
        try:
            data = self.fetch(DEFAULT_SOURCE)
        except Exception:                             # a bad snapshot is no worse than none
            return None
        if data is not None and not problems(data):
            log.warning("capability: using the snapshot shipped with the app until %s can be read", self.source)
            return data
        return None
