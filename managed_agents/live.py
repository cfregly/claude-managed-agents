"""The one real end-to-end run, behind --live.

It provisions a real environment, a real agent, and a real session, runs a single trivial turn,
prints what came back, then tears down what it can. Sessions and environments delete cleanly.
Agents have no delete, only archive, so the smoke archives the agent (read-only, unreferenceable
by new sessions). Teardown is best-effort and each step reports whether it succeeded, so a failed
cleanup never hides the result of the run.

This is the honest proof that the surface works. Everything else in the repo is an offline dry run
of a request shape. Live mode needs ANTHROPIC_API_KEY and the Managed Agents beta on your org.
"""

from .client import FAST_MODEL

KICKOFF = "Run `echo managed-agents-ok` with bash and tell me the exact output, nothing else."


def _safe(label, fn, *args, **kwargs):
    try:
        fn(*args, **kwargs)
        return f"  {label}: ok"
    except Exception as exc:  # best-effort cleanup, report rather than raise
        return f"  {label}: skipped ({exc.__class__.__name__})"


def live_smoke(client) -> str:
    env = client.beta.environments.create(
        name="claude-managed-agents-smoke",
        config={"type": "cloud", "networking": {"type": "unrestricted"}},
    )
    agent = client.beta.agents.create(
        name="claude-managed-agents-smoke",
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
