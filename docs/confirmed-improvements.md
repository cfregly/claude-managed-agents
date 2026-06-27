# Confirmed Improvements

Checked on 2026-06-26.

Current status: candidate. No promoted Managed Agents improvement is claimed yet.

The value bar is adversarially-confirmed to add value.

## Promotion Bar

A Managed Agents improvement is promoted only when it clears the repo bar:

- same workload, same model family, self-managed loop versus Managed Agents path
- same workload against OpenAI's strongest current agent stack
- same workload against Gemini's strongest current agent stack
- live model call, not only static review
- explicit baseline control path
- reproducible receipt with environment id, agent id, session id, and teardown result
- skeptical check that tries the self-managed loop or simpler Messages API path
- value maps to reliability, durability, operational simplicity, speed, or lower glue code

## Current Evidence

The repo is mechanically checked:

- `python scripts/deslop_check.py`
- `python -m compileall managed_agents run.py scripts`
- `python -m unittest discover -s tests -q`
- `env -u ANTHROPIC_API_KEY PYTHON_DOTENV_DISABLED=1 python run.py`
- `env -u ANTHROPIC_API_KEY PYTHON_DOTENV_DISABLED=1 python run.py compare`

The live smoke provisions an environment, agent, and session, sends one turn, streams to idle, and
tears down. That proves the core path for a run. It does not yet prove that hosted agent loops are
better than a self-managed loop, OpenAI's agent stack, or Gemini's agent stack for a founder
workload.

The comparison harness now runs one deterministic ops-triage workload across Claude Managed Agents,
a self-managed Claude Messages tool loop, OpenAI Agents SDK, and Google ADK with Gemini. The receipt
records model id, stack, latency, tool calls, correctness, failure reason, and teardown. Missing keys,
missing beta access, package incompatibility, or provider model access mark an arm `held`, not
promoted.

Latest local comparison on 2026-06-27:

- Command: `ANTHROPIC_API_KEY=... OPENAI_API_KEY=... GEMINI_API_KEY=... python run.py compare --live --providers managed,self-managed,openai,gemini`
- Result: mechanically vetted. All four arms returned the expected incident report for the same
  ops-triage workload.
- Promotion status: still candidate. The receipt proves the cross-stack harness and correctness
  gate. It does not yet prove hosted-loop value such as lower glue code, cleaner teardown, durable
  state, lower failure rate, or faster time to idle.

## Candidate Workloads

Managed Agents should be evaluated on workloads where hosting the loop matters:

- long-running support or ops agents that need session state
- workflows that need hosted tools, files, or memory resources
- multi-step research where cleanup and durable state matter
- internal agents where a team wants less orchestration code

## No Promoted Wins Yet

No row is promoted until a receipt shows:

- baseline self-managed loop result
- OpenAI agent-stack result
- Gemini agent-stack result
- Managed Agents result
- reliability, latency, cost, or code-surface comparison
- teardown and cleanup behavior
- failure mode where Managed Agents should not be used

Until then, this ledger records candidate evidence only.
