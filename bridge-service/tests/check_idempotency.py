"""Assert webhook idempotency store claim/expire/evict semantics.

Run: PYTHONPATH=. python tests/check_idempotency.py
"""

from __future__ import annotations

import importlib.util
import sys
import time
from pathlib import Path

_STORE = Path(__file__).resolve().parents[1] / "app" / "core" / "idempotency.py"


def _load_store():
    """Load IdempotencyStore without importing app (Flask is a runtime dep)."""
    spec = importlib.util.spec_from_file_location("idempotency", _STORE)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.IdempotencyStore


def main() -> None:
    IdempotencyStore = _load_store()

    store = IdempotencyStore(ttl_seconds=0.05, max_entries=2)
    assert store.claim("feishu:om_1") is True
    assert store.claim("feishu:om_1") is False
    assert store.claim("feishu:om_2") is True
    assert store.claim("feishu:om_3") is True
    # max_entries=2 evicted the oldest still-valid key
    assert store.claim("feishu:om_1") is True

    store.release("feishu:om_2")
    assert store.claim("feishu:om_2") is True

    short = IdempotencyStore(ttl_seconds=0.05, max_entries=8)
    assert short.claim("k") is True
    time.sleep(0.06)
    assert short.claim("k") is True

    print("idempotency checks passed")


if __name__ == "__main__":
    main()
