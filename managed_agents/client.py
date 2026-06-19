"""Anthropic client and model routing for the Managed Agents smoke.

This is a real tool. Every run calls the Managed Agents API, so ANTHROPIC_API_KEY is required and
the Managed Agents beta must be enabled on your org. If the key is missing, the run fails fast with
a clear error and a non-zero exit. There is no offline mode and no fallback. The SDK sets the
`managed-agents-2026-04-01` beta header automatically on
`client.beta.{agents,sessions,environments,memory_stores}.*` calls.
"""

import os
from pathlib import Path

try:  # honor this repo's ignored .env without weakening the fail-fast path
    from dotenv import load_dotenv

    if os.environ.get("PYTHON_DOTENV_DISABLED") != "1":
        load_dotenv(Path(__file__).resolve().parents[1] / ".env")
except Exception:  # pragma: no cover - dotenv is a setup helper, not the runtime contract
    pass

# The smoke runs the agent on the fast tier to stay cheap. Managed Agents needs a Claude 4.5+ model.
FAST_MODEL = "claude-haiku-4-5"
MAIN_MODEL = "claude-opus-4-8"


def require_key() -> None:
    """Raise immediately if ANTHROPIC_API_KEY is missing, so the run fails fast."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError(
            "ANTHROPIC_API_KEY is required (and the Managed Agents beta must be enabled on your "
            "org). Put it in .env or set it in the environment, then run `python run.py`."
        )


def get_client():
    """Return a real Anthropic client. Fails fast if the key is missing."""
    require_key()
    import anthropic

    return anthropic.Anthropic()
