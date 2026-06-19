# claude-managed-agents

[![ci](https://github.com/cfregly/claude-managed-agents/actions/workflows/ci.yml/badge.svg)](https://github.com/cfregly/claude-managed-agents/actions/workflows/ci.yml)
[![license: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

A runnable, honest tour of the **Managed Agents** surface. Managed Agents is the tier where
Anthropic runs the agent loop and hosts a per-session container where the agent's tools execute.
This repo runs one real end-to-end smoke against that surface and documents the eleven request
shapes you compose to use it.

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

ANTHROPIC_API_KEY=... python run.py            # provision a real env + agent + session, one turn, then teardown
ANTHROPIC_API_KEY=... python run.py --cleanup  # sweep leftover smoke resources from a failed run
```

This is a real tool. Every run calls the Managed Agents API, so `ANTHROPIC_API_KEY` is required
and the `managed-agents-2026-04-01` beta must be enabled on your org. Without a key it fails fast
with a clear error and a non-zero exit. There is no offline mode and no fallback. The smoke names
its environment and agent with a per-run suffix and tears them down at the end (sessions and
environments delete, the agent is archived). If a run crashes mid-way, `--cleanup` archives any
stranded smoke agents and deletes any stranded smoke environments.

## Verify it

```bash
python scripts/deslop_check.py
python -m compileall managed_agents run.py scripts
python -m unittest discover -s tests -q
env -u ANTHROPIC_API_KEY PYTHON_DOTENV_DISABLED=1 python run.py  # should fail fast, non-zero
```

## What the smoke does

`run.py` provisions a real environment, a real agent, and a real session, sends one message,
streams the reply over SSE to idle, then tears everything down and reports each teardown step. It
exercises the core path (agent lifecycle, environment, session, the event stream) end to end.

## The eleven surfaces (request-shape reference)

The smoke runs the core path live. The rest of the surface composes from these shapes, kept current
against the `managed-agents-2026-04-01` beta.

| Surface | Shape |
|---|---|
| `agent_lifecycle` | `client.beta.agents.create(name=, model=, tools=[{"type":"agent_toolset_20260401"}])`. Create once, reference by id and version. Anti-pattern: create per request. |
| `environment` | `client.beta.environments.create(name=, config={"type":"cloud","networking":{"type":"unrestricted"}})`. Cloud or self_hosted, networking unrestricted or limited. |
| `session` | `client.beta.sessions.create(agent=agent.id, environment_id=env.id, title=)`. One stateful run. Lifecycle: rescheduling, running, idle, terminated. |
| `events_stream` | `with client.beta.sessions.events.stream(session_id=s.id) as stream:` then `events.send(... user.message ...)`. Read `agent.message`, stop on `session.status_idle`. |
| `custom_tools` | on `agent.custom_tool_use`, send `{"type":"user.custom_tool_result","custom_tool_use_id":id,"content":[...]}`. Anthropic tools run in the container, custom ones run on you. |
| `memory_store` | `client.beta.memory_stores.create(name=, description=)`, then attach via `resources=[{"type":"memory_store","memory_store_id":store.id,"access":"read_write"}]`. Mounts at `/mnt/memory/`. |
| `vault_and_mcp` | agent `mcp_servers=[{"type":"url","name":"linear","url":...}]` plus `tools=[{"type":"mcp_toolset","mcp_server_name":"linear"}]`, session `vault_ids=[vault.id]`. The credential never enters the prompt or the container. |
| `resources` | `resources=[{"type":"file","file_id":f.id,"mount_path":"/workspace/data.csv"}]` and `github_repository`. Outputs land in `/mnt/session/outputs/`, fetched with `files.list(scope_id=session.id)`. |
| `outcomes` | send `{"type":"user.define_outcome","description":,"rubric":{"type":"text","content":RUBRIC},"max_iterations":5}`. A grader scores each iteration, watch `span.outcome_evaluation_end.result`. |
| `multiagent` | `multiagent={"type":"coordinator","agents":[reviewer.id, {"type":"agent","id":tester.id,"version":4}, {"type":"self"}]}`. Top-level agent field, one level of delegation, threads share the filesystem. |
| `cli_yaml` | control plane in YAML via the `ant` CLI: `ant beta:agents create < agent.yaml --transform id -r`, then `ant beta:agents update --agent-id $ID --version 1 < agent.yaml`. The SDK drives the data plane. |

The repo also ships a `verify` skill and a Stop hook under `.claude/`, which is the skills and
hooks feature demonstrating itself.

## Layout

```
managed_agents/
  client.py    # the real client, key required, and model routing
  live.py      # the end-to-end smoke and the --cleanup sweep, with best-effort teardown
run.py         # one-command entry: the live smoke, or --cleanup
tests/         # offline parser tests
scripts/       # the self-contained deslop gate for CI
.claude/       # the verify skill and the Stop hook (skills + hooks, demonstrated)
```

## License

MIT.
