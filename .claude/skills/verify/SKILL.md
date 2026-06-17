---
name: verify
description: Use this skill to verify the surface tour whenever you add a surface, change a request shape, or touch the runner or the live smoke. Run it aggressively any time you touch relevant code.
---

Verify the repo with these tools, in order. Do not stop until they pass.

1. Run the offline dry run: `python run.py`. Every surface must print and the receipt at
   data/last_run.md must refresh.
2. Run the deslop gate on the docs: `python scripts/deslop_check.py`. It must be clean.
3. Read the README surface table against the code in `managed_agents/surfaces.py`. If a row and
   the code disagree, fix the row. The repo lists only the surfaces it actually shows, and labels
   Managed Agents as the beta it is.
4. Check that the dry path provisions nothing: every surface function takes `client` but returns a
   `[dry]` shape, and only `live.py` touches the API. Going live must stay opt-in behind `--live`.
5. If you touched the live smoke, run `python run.py --live` once and confirm it provisions, runs a
   turn, and then reports a clean teardown for the session, the environment, and the agent.

If you hit a blocker, find a solution and update this skill for the future, so the next change
verifies itself. This skill is meant to improve, not stay frozen.
