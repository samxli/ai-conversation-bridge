"""Assert run_coroutine cancels the asyncio task when the wait timeout fires.

Run: PYTHONPATH=. python tests/check_async_runner.py
"""

from __future__ import annotations

import asyncio
import importlib.util
import sys
import threading
from pathlib import Path

_RUNNER = Path(__file__).resolve().parents[1] / "app" / "core" / "async_runner.py"


def _load_runner():
    """Load async_runner without importing app (Flask is a runtime dep)."""
    spec = importlib.util.spec_from_file_location("async_runner", _RUNNER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.run_coroutine


def main() -> None:
    run_coroutine = _load_runner()
    cancelled = threading.Event()

    async def hang() -> None:
        try:
            await asyncio.sleep(60)
        except asyncio.CancelledError:
            cancelled.set()
            raise

    try:
        run_coroutine(hang(), timeout=0.2)
        raise AssertionError("expected TimeoutError")
    except TimeoutError:
        pass

    assert cancelled.wait(timeout=2.0), "timed-out coroutine was not cancelled"
    print("async runner timeout cancel checks passed")


if __name__ == "__main__":
    main()
