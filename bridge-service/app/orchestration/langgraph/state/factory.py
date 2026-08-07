"""LangGraph checkpointer factory."""

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver

from app.config import Config


def make_checkpointer(config: type[Config] = Config) -> BaseCheckpointSaver:
    """Return a checkpointer for STATE_BACKEND, or raise for unsupported values."""
    backend = config.STATE_BACKEND
    if backend == "memory":
        return InMemorySaver()
    if backend == "firestore":
        from app.orchestration.langgraph.state.firestore import FirestoreCheckpointer

        return FirestoreCheckpointer()
    raise SystemExit(
        f"Unsupported STATE_BACKEND={backend!r}. Supported values: memory."
    )
