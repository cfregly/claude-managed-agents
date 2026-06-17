"""One function per Managed Agents surface.

Each prints the mechanism and the exact, current request shape, so you can read the whole surface
offline without provisioning anything. The request shapes are kept correct against the
`managed-agents-2026-04-01` beta so they are copy-pasteable. The end-to-end live run lives in
live.py, because the surfaces compose (no session without an agent and an environment) and running
each one live in isolation would leave orphaned cloud objects.
"""


def _dry(*lines):
    return "\n".join("[dry] " + line for line in lines)


def agent_lifecycle(client):
    return _dry(
        "An agent is a persisted, versioned object. Create it once, reference it by id forever.",
        "The config is flat: model, system, tools, mcp_servers, skills are top-level on the agent.",
        "Anti-pattern: agents.create() per request. Hoist it to setup, store the id and version.",
        'agent = client.beta.agents.create(name="Reviewer", model="claude-opus-4-8",',
        '    tools=[{"type":"agent_toolset_20260401","default_config":{"enabled":True}}])',
        "Each update is a new immutable version. Pin a session to a version for reproducibility.",
    )


def environment(client):
    return _dry(
        "An environment is a reusable template for the container where the agent's tools run.",
        "config.type is cloud (Anthropic runs it) or self_hosted (your infra, you control egress).",
        "Networking is unrestricted, or limited, which is deny-by-default plus allowed_hosts.",
        'env = client.beta.environments.create(name="dev",',
        '    config={"type":"cloud","networking":{"type":"unrestricted"}})',
        "The agent loop runs on Anthropic's side and acts on this container through tool calls.",
    )


def session(client):
    return _dry(
        "A session is one stateful run of an agent inside an environment. No agent, no session.",
        "Reference the agent by id (latest version) or {type:agent,id,version} to pin a version.",
        "Lifecycle: rescheduling -> running <-> idle -> terminated. Errors are session.error events.",
        'session = client.beta.sessions.create(agent=agent.id, environment_id=env.id, title="task")',
        "Built in: context compaction near the limit, prompt caching of history, thinking on.",
    )


def events_stream(client):
    return _dry(
        "A session is driven by events over SSE. Open the stream before you send, or early events batch.",
        "Send a user.message, read agent.message text blocks, stop on session.status_idle.",
        "with client.beta.sessions.events.stream(session_id=s.id) as stream:",
        '    client.beta.sessions.events.send(session_id=s.id, events=[',
        '        {"type":"user.message","content":[{"type":"text","text":"Review the auth module"}]}])',
        "Watch agent.message (text out), session.status_idle (done), session.status_terminated (over).",
    )


def custom_tools(client):
    return _dry(
        "Declare a custom tool on the agent. Anthropic tools run in the container, custom ones run on you.",
        "On agent.custom_tool_use the session goes idle. Run the tool, then send the result back by id.",
        '{"type":"user.custom_tool_result","custom_tool_use_id":id,',
        '    "content":[{"type":"text","text":"All 42 tests passed."}]}',
        "Loop: stream until idle, collect tool calls, send results, stream again, until no calls remain.",
    )


def memory_store(client):
    return _dry(
        "A memory store is workspace-scoped text that persists across sessions (beta managed-agents-2026-04-01).",
        "Attach it via resources at session-create time. It mounts at /mnt/memory/<name>/ as files.",
        "The agent reads and writes it with ordinary file tools. There are no dedicated memory tools.",
        'store = client.beta.memory_stores.create(name="prefs", description="per-user context")',
        'resources=[{"type":"memory_store","memory_store_id":store.id,"access":"read_write"}]',
        "Every mutation is an immutable memory version: an audit trail, with redaction for PII or secrets.",
    )


def vault_and_mcp(client):
    return _dry(
        "An agent declares an MCP server. The credential never goes in the prompt or the agent config.",
        "Attach a vault to the session with vault_ids. The vault holds the credential, injected at egress.",
        'agent: mcp_servers=[{"type":"url","name":"linear","url":"https://mcp.linear.app/sse"}]',
        'agent: tools=[{"type":"mcp_toolset","mcp_server_name":"linear"}]',
        "session = client.beta.sessions.create(agent=agent.id, environment_id=env.id, vault_ids=[vault.id])",
        "Code in the container, including code the agent writes, cannot read the credential.",
    )


def resources(client):
    return _dry(
        "Attach files, GitHub repos, and memory stores at startup. Creation blocks until all are mounted.",
        "A file uploads once via the Files API, then mounts read-only by file_id at an absolute mount_path.",
        "A github_repository clones into the container. An Anthropic git proxy injects the token at egress.",
        "The agent writes outputs to /mnt/session/outputs/. Fetch them with files.list(scope_id=session.id).",
        'resources=[{"type":"file","file_id":f.id,"mount_path":"/workspace/data.csv"}]',
    )


def outcomes(client):
    return _dry(
        "An outcome turns a session from conversation into graded work. You state what done looks like.",
        "Send user.define_outcome with a rubric. A separate grader scores each iteration and feeds back gaps.",
        "The loop runs iterate -> grade -> revise until satisfied, max_iterations, or failed.",
        '{"type":"user.define_outcome","description":"Build a DCF model in .xlsx",',
        '    "rubric":{"type":"text","content":RUBRIC_MD},"max_iterations":5}',
        "Watch span.outcome_evaluation_end.result: satisfied, needs_revision, max_iterations_reached, failed.",
    )


def multiagent(client):
    return _dry(
        "A coordinator delegates to a roster of agents in one session. They share the container filesystem.",
        "multiagent is a top-level field on the agent, not a tools entry and not on the session.",
        "Each subagent runs in its own thread, with its own context, model, and tools. One level deep only.",
        'multiagent={"type":"coordinator","agents":[reviewer.id,',
        '    {"type":"agent","id":tester.id,"version":4}, {"type":"self"}]}',
        "Watch session.thread_created and agent.thread_message_received. Up to 25 concurrent threads.",
    )


def cli_yaml(client):
    return _dry(
        "Split the work: the ant CLI for the control plane, the SDK for the data plane.",
        "Agents and environments are static. Define them as YAML, check it in, apply from CI with ant.",
        "Sessions are dynamic. Create them per task from your app with the SDK.",
        "ant beta:agents create < agent.yaml --transform id -r       # create once, capture the id",
        "ant beta:agents update --agent-id $ID --version 1 < agent.yaml   # optimistic-locked update",
    )


REGISTRY = {
    "agent_lifecycle": ("create once, reference by id and version", agent_lifecycle),
    "environment": ("the reusable container template", environment),
    "session": ("one stateful run of an agent", session),
    "events_stream": ("drive a session over SSE, stream-first", events_stream),
    "custom_tools": ("your client runs the custom tool, result by id", custom_tools),
    "memory_store": ("text that persists across sessions", memory_store),
    "vault_and_mcp": ("MCP server on the agent, credential in a vault", vault_and_mcp),
    "resources": ("mount files and repos, capture outputs", resources),
    "outcomes": ("graded work with an iterate-grade-revise loop", outcomes),
    "multiagent": ("a coordinator delegates to a roster", multiagent),
    "cli_yaml": ("control plane in YAML via the ant CLI", cli_yaml),
}
