"""In-process webhook delivery dedup (GitHub issue #60)."""

import threading
import time
from collections import OrderedDict


class IdempotencyStore:
    """Bounded TTL set. claim() is True for a new key, False for a duplicate.

    ponytail: process-local only — extra Cloud Run instances miss each other.
    Upgrade: shared Redis SET NX + TTL when max-instances > 1.
    """

    def __init__(self, ttl_seconds: float = 6 * 3600, max_entries: int = 4096):
        """Store keys until ttl_seconds elapses, evicting oldest beyond max_entries."""
        self._ttl = ttl_seconds
        self._max = max_entries
        self._lock = threading.Lock()
        self._entries: OrderedDict[str, float] = OrderedDict()

    def claim(self, key: str) -> bool:
        """Return True if this key is new (caller should process), False if duplicate."""
        now = time.monotonic()
        with self._lock:
            self._purge(now)
            expires = self._entries.get(key)
            if expires is not None and expires > now:
                return False
            self._entries[key] = now + self._ttl
            self._entries.move_to_end(key)
            while len(self._entries) > self._max:
                self._entries.popitem(last=False)
            return True

    def release(self, key: str) -> None:
        """Drop a claimed key so a failed delivery can be retried."""
        with self._lock:
            self._entries.pop(key, None)

    def _purge(self, now: float) -> None:
        """Drop expired keys from the oldest end of the map."""
        while self._entries:
            key, expires = next(iter(self._entries.items()))
            if expires > now:
                break
            del self._entries[key]
