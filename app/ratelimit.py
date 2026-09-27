"""Small in-memory rate limiter to protect the Azure bill on a public endpoint.

Two limits: per client IP per minute, and a global daily cap. State lives in
process memory, which is fine for a single free Render instance (it resets on
restart). A multi-instance deployment would need a shared store such as Redis.
"""
import threading
import time
from collections import defaultdict, deque


class RateLimiter:
    def __init__(self, per_minute=6, per_day=300, clock=time.time):
        self.per_minute = per_minute
        self.per_day = per_day
        self.clock = clock
        self._hits = defaultdict(deque)
        self._day = None
        self._day_count = 0
        self._lock = threading.Lock()

    def allow(self, client_id):
        """Return (allowed, reason). Records the hit only if allowed."""
        now = self.clock()
        with self._lock:
            day = int(now // 86400)
            if day != self._day:
                self._day, self._day_count = day, 0
            if self._day_count >= self.per_day:
                return False, "Daily question limit reached. Please try again tomorrow."
            hits = self._hits[client_id]
            while hits and now - hits[0] >= 60:
                hits.popleft()
            if len(hits) >= self.per_minute:
                return False, "Too many questions in a minute. Please wait a moment."
            hits.append(now)
            self._day_count += 1
            return True, ""
