"""Shared asyncio event loop for sync Flask routes calling async orchestrators."""

from __future__ import annotations

import asyncio
import logging
import threading
from collections.abc import Coroutine
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

_loop: asyncio.AbstractEventLoop | None = None
_thread: threading.Thread | None = None
_lock = threading.Lock()


def start_background_loop() -> asyncio.AbstractEventLoop:
    """Start a daemon thread with a long-lived event loop; return that loop."""
    global _loop, _thread
    with _lock:
        if _loop is not None and _loop.is_running():
            return _loop

        loop = asyncio.new_event_loop()

        def _run() -> None:
            asyncio.set_event_loop(loop)
            loop.run_forever()

        thread = threading.Thread(target=_run, name="bridge-asyncio", daemon=True)
        thread.start()
        _loop = loop
        _thread = thread
        logger.info("Started background asyncio event loop for orchestration")
        return loop


def get_loop() -> asyncio.AbstractEventLoop:
    """Return the shared loop, starting it if needed."""
    global _loop
    if _loop is None or not _loop.is_running():
        return start_background_loop()
    return _loop


def run_coroutine(coro: Coroutine[Any, Any, T], timeout: float | None = None) -> T:
    """Submit a coroutine to the shared loop and block until it completes."""
    loop = get_loop()
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    return future.result(timeout=timeout)
