# CLAUDE.md

Conventions for any agent working on `claude-managed-agents`. Read this first.

## What this is

A runnable, honest tour of the Managed Agents surface. `run.py` runs one real end-to-end smoke
(provision an environment, an agent, and a session, send one turn, stream the reply, tear down),
and the README documents the eleven request shapes you compose to use the full surface. Managed
Agents ships under the `managed-agents-2026-04-01` beta.

This is a standalone reference repo, a platform deep-dive alongside the `claude-founder-kit` main
kit, not part of it.

## Run it

    pip install -r requirements.txt
    ANTHROPIC_API_KEY=... python run.py            # the live smoke, end to end
    ANTHROPIC_API_KEY=... python run.py --cleanup  # sweep leftover smoke resources

## Rules

- Key required, fail fast. Every run calls the real Managed Agents API, so `ANTHROPIC_API_KEY` is
  required and the beta must be enabled on your org. Without a key the run fails fast with a clear
  error and a non-zero exit. There is no offline mode and no fallback.
- Live cleans up after itself. The smoke names resources with a per-run suffix, deletes the session
  and environment, and archives the agent (agents have no delete). Teardown is best-effort and
  reports each step. `--cleanup` sweeps anything a crashed run stranded.
- Shapes are current, not invented. The README shapes track the `managed-agents-2026-04-01` beta.
  If the SDK surface moves, fix the shape rather than guess.
- Claim only what runs. The smoke reports the real env, agent, session ids, the agent reply, and
  the teardown result. Nothing is simulated.
- Prose is deslop-clean: no em-dashes, no en-dashes, no semicolons, no buzzwords. CI runs the
  deslop gate on the README and this file, a compile check, and a fail-fast-without-a-key check.
- Never commit a key. `.env` stays git-ignored.
