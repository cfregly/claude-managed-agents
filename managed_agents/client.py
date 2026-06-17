"""Anthropic client and model routing for the Managed Agents smoke.

This is a real tool. Every run calls the Managed Agents API, so ANTHROPIC_API_KEY is required and
the Managed Agents beta must be enabled on your org. If the key is missing, the run fails fast with
a clear error and a non-zero exit. There is no offline mode and no fallback. The SDK sets the
`managed-agents-2026-04-01` beta header automatically on
`client.beta.{agents,sessions,environments,memory_stores}.*` calls.
"""

import os

# The smoke runs the agent on the fast tier to stay cheap. Managed Agents needs a Claude 4.5+ model.
FAST_MODEL = "claude-haiku-4-5"
MAIN_MODEL = "claude-opus-4-8"


def require_key() -> None:
    """Raise immediately if ANTHROPIC_API_KEY is missing, so the run fails fast."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError(
            "ANTHROPIC_API_KEY is required (and the Managed Agents beta must be enabled on your "
            "org). Set it, then run `ANTHROPIC_API_KEY=... python run.py`."
        )


def get_client():
    """Return a real Anthropic client. Fails fast if the key is missing."""
    require_key()
    import anthropic

    return anthropic.Anthropic()
