# CLAUDE.md

Conventions for any agent working on `claude-managed-agents`. Read this first.

## What this is

A runnable, honest tour of the Managed Agents surface, in one repo. The agent lifecycle,
environments, sessions, the event stream, custom tools, memory stores, vaults and MCP, resource
mounts, outcomes, multiagent coordinators, and the `ant` CLI control plane. Each surface prints
the mechanism and the exact request shape offline, and one real end-to-end run lives behind
`--live`.

This is a standalone reference repo, a bonus alongside the six `claude-startup-*` repos, not one
of them. Managed Agents ships under the `managed-agents-2026-04-01` beta, and the repo labels it.

## Run it

    pip install -r requirements.txt
    python run.py                 # offline, every surface as a dry run
    python run.py memory_store    # one surface, dry run
    ANTHROPIC_API_KEY=... python run.py --live   # real env + agent + session, one turn, teardown

## Rules

- Runs in one command. `python run.py` works with no key and prints every surface's request shape.
- Going live is opt-in. Only `--live` constructs a real client, so no run provisions a real
  environment, agent, or session by accident.
- Live cleans up after itself. The smoke deletes the session and environment and archives the
  agent (agents have no delete). Teardown is best-effort and reports each step.
- Shapes are correct, not invented. The request shapes track the `managed-agents-2026-04-01` beta.
  If the SDK surface moves, fix the shape rather than guess.
- Claim only what runs. The dry run simulates and labels every line `[dry]`. The live run is the
  only thing that touches the API.
- Prose is deslop-clean: no em-dashes, no en-dashes, no semicolons, no buzzwords. CI runs the
  deslop gate on the README and this file.
- Never commit a key. `.env` stays git-ignored.
