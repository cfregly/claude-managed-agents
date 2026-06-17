# claude-managed-agents

A runnable, honest tour of the **Managed Agents** surface, in one repo. Managed Agents is the
tier where Anthropic runs the agent loop and hosts a per-session container where the agent's tools
execute. This repo shows each part of that surface as a small, correct request shape you can read
offline, and a single real end-to-end run behind `--live`.

```bash
pip install -r requirements.txt

python run.py                  # offline: every surface, as a dry run of its request shape
python run.py memory_store     # one surface, dry run
ANTHROPIC_API_KEY=... python run.py --live   # real env + agent + session, one turn, then teardown
```

## A note on honesty

This is a standalone reference repo, a bonus alongside the six `claude-startup-*` repos, not one
of them. Managed Agents ships under the `managed-agents-2026-04-01` beta, and the repo says so. The
request shapes are kept correct against that beta. The offline run prints `[dry]` on every line it
simulates and provisions nothing. `--live` provisions real cloud resources (an environment, an
agent, a session), runs one trivial turn, and then tears them down best-effort: sessions and
environments delete, and because agents have no delete it archives the agent. Each teardown step
reports whether it succeeded, so a failed cleanup never hides the result.

## The surface

| Surface | What the demo shows |
|---|---|
| `agent_lifecycle` | the agent as a persisted, versioned object: create once, reference by id |
| `environment` | the reusable container template, cloud or self-hosted, networking policy |
| `session` | one stateful run of an agent in an environment, and its lifecycle states |
| `events_stream` | driving a session over SSE, stream-first, reading `agent.message` to idle |
| `custom_tools` | the custom-tool loop: `agent.custom_tool_use` then `user.custom_tool_result` |
| `memory_store` | text that persists across sessions, mounted as files at `/mnt/memory/` |
| `vault_and_mcp` | an MCP server on the agent, its credential held in a vault, not the prompt |
| `resources` | mounting files and GitHub repos, capturing `/mnt/session/outputs/` |
| `outcomes` | graded work: `user.define_outcome` with a rubric and an iterate-grade-revise loop |
| `multiagent` | a coordinator delegating to a roster of agents, one level deep, over threads |
| `cli_yaml` | the control plane in version-controlled YAML via the `ant` CLI |

The repo also ships a `verify` skill and a Stop hook under `.claude/`, which is the skills and
hooks feature demonstrating itself.

## Layout

```
managed_agents/
  client.py     # the client, or None for the offline dry run, and model routing
  surfaces.py   # one function per surface, plus the registry
  live.py       # the one real end-to-end run, with best-effort teardown
run.py          # one-command entry: every surface dry, or one, or the live smoke
scripts/        # the self-contained deslop gate for CI
.claude/        # the verify skill and the Stop hook (skills + hooks, demonstrated)
```

## License

MIT.
