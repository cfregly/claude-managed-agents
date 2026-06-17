"""Anthropic client and model routing for the Managed Agents demos.

Going live is opt-in: `get_client` returns None unless a run uses `--live`, so no run provisions a
real environment, agent, or session by accident. Live mode also needs the Managed Agents beta
enabled on your org. The SDK sets the `managed-agents-2026-04-01` beta header automatically on
`client.beta.{agents,sessions,environments,memory_stores}.*` calls.
"""

import os

# The agent runs on a frontier-capable model. The smoke uses the fast tier to stay cheap; the dry
# shapes show Opus, which is what the docs use. Managed Agents needs a Claude 4.5+ model.
FAST_MODEL = "claude-haiku-4-5"
MAIN_MODEL = "claude-opus-4-8"


def key_present() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def get_client(live: bool = False):
    if not live:
        return None
    if not key_present():
        raise RuntimeError("live mode needs ANTHROPIC_API_KEY in the environment")
    import anthropic

    return anthropic.Anthropic()
