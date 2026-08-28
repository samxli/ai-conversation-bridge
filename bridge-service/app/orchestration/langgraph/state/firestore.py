"""Firestore checkpointer stub — not implemented in this reference release.

Use STATE_BACKEND=memory for the single-instance reference deploy. For durable
state, see docs/enterprise-guide.md (conversation-state retention).
"""


def FirestoreCheckpointer(*args, **kwargs):
    """Placeholder for a future Firestore-backed BaseCheckpointSaver."""
    raise NotImplementedError(
        "STATE_BACKEND=firestore is not implemented. "
        "Use STATE_BACKEND=memory for the reference architecture, or see "
        "docs/enterprise-guide.md for durable-state guidance."
    )
