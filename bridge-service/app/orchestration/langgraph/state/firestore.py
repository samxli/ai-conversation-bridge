"""Firestore checkpointer stub — not implemented in this reference release.

See docs/langgraph-orchestration-proposal-v2.md §6.3 for the durable-state
discussion. Use STATE_BACKEND=memory for the single-instance reference deploy.
"""


def FirestoreCheckpointer(*args, **kwargs):
    """Placeholder for a future Firestore-backed BaseCheckpointSaver."""
    raise NotImplementedError(
        "STATE_BACKEND=firestore is not implemented. "
        "Use STATE_BACKEND=memory for the reference architecture, or see "
        "docs/langgraph-orchestration-proposal-v2.md for the durable-store design."
    )
