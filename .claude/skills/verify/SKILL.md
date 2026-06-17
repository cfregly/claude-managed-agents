---
name: verify
description: Use this skill to verify the smoke whenever you change the live run, the teardown, or the runner. Run it aggressively any time you touch relevant code.
---

Verify the repo with these tools, in order. Do not stop until they pass.

1. Run the smoke: `ANTHROPIC_API_KEY=... python run.py`. It needs a key and the Managed Agents
   beta, calls the real API, and must provision, run one turn, then report a clean teardown for
   the session, the environment, and the agent. Refresh the receipt at data/last_run.md. Without a
   key the run must fail fast with a clear key-required message and a non-zero exit.
2. Run the deslop gate on the docs: `python scripts/deslop_check.py`. It must be clean. Offline.
3. Run the compile check: `python -m compileall managed_agents run.py scripts`. It must succeed. Offline.
4. Read the README surface reference against the live path in `managed_agents/live.py`. The smoke
   exercises the core path; the README shapes document the rest. If a shape and the SDK disagree,
   fix the shape.
5. After a real run, confirm `python run.py --cleanup` finds nothing left (the smoke tore itself
   down). If it sweeps something, the teardown regressed.

If no key is available, run the offline gates (steps 2 and 3) and confirm step 1 fails fast with
the key-required message under `env -u ANTHROPIC_API_KEY python run.py`. Do not fake a run.

If you hit a blocker, find a solution and update this skill for the future, so the next change
verifies itself. This skill is meant to improve, not stay frozen.
