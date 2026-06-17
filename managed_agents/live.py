"""The one real end-to-end run, behind --live.

It provisions a real environment, a real agent, and a real session, runs a single trivial turn,
prints what came back, then tears down what it can. Sessions and environments delete cleanly.
Agents have no delete, only archive, so the smoke archives the agent (read-only, unreferenceable
by new sessions). Teardown is best-effort and each step reports whether it succeeded, so a failed
cleanup never hides the result of the run.

This is the honest proof that the surface works. Everything else in the repo is an offline dry run
of a request shape. Live mode needs ANTHROPIC_API_KEY and the Managed Agents beta on your org.
"""

import uuid

from .client import FAST_MODEL

SMOKE_PREFIX = "claude-managed-agents-smoke"
KICKOFF = "Run `echo managed-agents-ok` with bash and tell me the exact output, nothing else."


def _safe(label, fn, *args, **kwargs):
    try:
        fn(*args, **kwargs)
        return f"  {label}: ok"
    except Exception as exc:  # best-effort cleanup, report rather than raise
        return f"  {label}: skipped ({exc.__class__.__name__})"


def live_smoke(client) -> str:
    # A unique tag per run, so a failed teardown never 409s the next run on the environment name.
    tag = f"{SMOKE_PREFIX}-{uuid.uuid4().hex[:8]}"
    env = client.beta.environments.create(
        name=tag,
        config={"type": "cloud", "networking": {"type": "unrestricted"}},
    )
    agent = client.beta.agents.create(
        name=tag,
        model=FAST_MODEL,
        system="You are a terse shell assistant. Run exactly what is asked and report the output.",
        tools=[{"type": "agent_toolset_20260401", "default_config": {"enabled": True}}],
    )
    session = client.beta.sessions.create(
        agent={"type": "agent", "id": agent.id, "version": agent.version},
        environment_id=env.id,
        title="managed-agents smoke",
    )

    reply = []
    try:
        # Stream-first: open the stream, then send, so no early event is missed.
        with client.beta.sessions.events.stream(session_id=session.id) as stream:
            client.beta.sessions.events.send(
                session_id=session.id,
                events=[{"type": "user.message", "content": [{"type": "text", "text": KICKOFF}]}],
            )
            for event in stream:
                if event.type == "agent.message":
                    for block in event.content:
                        if getattr(block, "type", "") == "text":
                            reply.append(block.text)
                elif event.type in ("session.status_idle", "session.status_terminated"):
                    break
    finally:
        teardown = [
            _safe("delete session", client.beta.sessions.delete, session_id=session.id),
            _safe("delete environment", client.beta.environments.delete, env.id),
            _safe("archive agent", client.beta.agents.archive, agent.id),
        ]

    text = "".join(reply).strip() or "(no text returned)"
    return (
        f"env={env.id}\nagent={agent.id} v{agent.version}\nsession={session.id}\n"
        f"agent reply: {text}\n"
        "teardown:\n" + "\n".join(teardown)
    )


def cleanup(client) -> str:
    """Sweep leftover smoke resources by name prefix.

    A clean --live run tears itself down, but a crash between create and teardown can strand a
    smoke agent (archivable, not deletable) or a smoke environment (whose unique name would 409
    the next run). This archives stranded agents and deletes stranded environments, then reports
    what it touched. Safe to run any time, even with nothing to clean.
    """
    archived = deleted = skipped = 0

    for agent in client.beta.agents.list():
        name = getattr(agent, "name", "") or ""
        if not name.startswith(SMOKE_PREFIX):
            continue
        if getattr(agent, "archived_at", None):
            skipped += 1
            continue
        try:
            client.beta.agents.archive(agent.id)
            archived += 1
        except Exception:
            skipped += 1

    for env in client.beta.environments.list():
        name = getattr(env, "name", "") or ""
        if not name.startswith(SMOKE_PREFIX):
            continue
        try:
            client.beta.environments.delete(env.id)
            deleted += 1
        except Exception:
            skipped += 1

    return f"cleanup: archived {archived} agent(s), deleted {deleted} environment(s), skipped {skipped}"
