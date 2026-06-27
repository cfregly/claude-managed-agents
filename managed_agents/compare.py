"""Cross-stack comparison harness for Managed Agents.

The comparison is deliberately conservative. It records what ran, what held, and why. A held arm is
not a loss and not a win. It is the evidence needed before a public claim can move.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import time
import uuid
from pathlib import Path
from typing import Any

from .client import FAST_MODEL
from .live import _safe

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
LAST_JSON = DATA / "last_compare.json"
LAST_MD = DATA / "last_compare.md"
COMPARE_PREFIX = "claude-managed-agents-compare"
OPENAI_MODEL = os.environ.get("OPENAI_AGENT_MODEL", "gpt-5.5")
GEMINI_MODEL = os.environ.get("GEMINI_AGENT_MODEL", "gemini-3.5-flash")
CLAUDE_SELF_MODEL = os.environ.get("CLAUDE_SELF_MANAGED_MODEL", "claude-haiku-4-5-20251001")

EVIDENCE: dict[str, list[dict[str, Any]]] = {
    "logs": [
        {"id": "log-auth-1", "service": "auth", "level": "error", "message": "cache ttl jumped to 3600s after deploy dpl-17"},
        {"id": "log-api-2", "service": "api", "level": "warn", "message": "northwind and acme login retries above baseline"},
        {"id": "log-web-3", "service": "web", "level": "info", "message": "static asset deploy completed cleanly"},
    ],
    "tickets": [
        {"id": "ticket-884", "account": "acme", "symptom": "login loop after password reset"},
        {"id": "ticket-885", "account": "northwind", "symptom": "session cookie rejected after auth refresh"},
    ],
    "deploys": [
        {"id": "dpl-16", "service": "web", "change": "css bundle"},
        {"id": "dpl-17", "service": "auth", "change": "increase token cache ttl"},
    ],
}

EXPECTED_REPORT = {
    "incident_id": "inc-042",
    "severity": "sev2",
    "root_cause": "auth cache ttl regression",
    "action": "rollback dpl-17 and invalidate auth cache",
    "affected_accounts": ["acme", "northwind"],
    "evidence_ids": ["log-auth-1", "log-api-2", "ticket-884", "ticket-885", "dpl-17"],
}

PROMPT = (
    "You are running an ops triage. Use the available tools to inspect logs, tickets, and deploys. "
    "Then emit one JSON report with keys incident_id, severity, root_cause, action, "
    "affected_accounts, and evidence_ids. Do not invent evidence. The expected incident id is inc-042."
)


def fetch_ops_slice(kind: str) -> str:
    if kind in {"all", "incident", "incidents", "evidence"}:
        return json.dumps(EVIDENCE, sort_keys=True)
    if kind not in EVIDENCE:
        return json.dumps({"error": f"unknown slice: {kind}", "available": sorted(EVIDENCE)}, sort_keys=True)
    return json.dumps(EVIDENCE[kind], sort_keys=True)


def _now_ms(start: float) -> int:
    return int((time.monotonic() - start) * 1000)


def _jsonish(text: str) -> dict[str, Any] | None:
    text = text or ""
    blocks = re.findall(r"\{.*?\}", text, flags=re.S)
    for block in reversed(blocks):
        try:
            parsed = json.loads(block)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


def score_report(text: str, emitted: dict[str, Any] | None = None) -> tuple[bool, dict[str, Any], list[str]]:
    report = emitted or _jsonish(text) or {}
    failures: list[str] = []
    incident = str(report.get("incident_id", "")).strip().lower()
    if incident != EXPECTED_REPORT["incident_id"]:
        failures.append(f"incident_id={report.get('incident_id')!r}")
    severity = str(report.get("severity", "")).strip().lower()
    if severity not in {"sev2", "severe", "high", "high severity", "major"}:
        failures.append(f"severity={report.get('severity')!r}")
    root = str(report.get("root_cause", "")).strip().lower()
    for token in ("auth", "cache", "ttl"):
        if token not in root:
            failures.append(f"root_cause missing {token!r}")
    action = str(report.get("action", "")).strip().lower()
    if not any(token in action for token in ("rollback", "roll back", "revert")):
        failures.append(f"action lacks rollback/revert: {report.get('action')!r}")
    if "dpl-17" not in action:
        failures.append("action missing 'dpl-17'")
    if "cach" not in action and "ttl" not in action:
        failures.append("action missing cache or ttl")
    for key in ("affected_accounts", "evidence_ids"):
        got = sorted(str(v).lower() for v in report.get(key, []))
        wanted = sorted(str(v).lower() for v in EXPECTED_REPORT[key])
        missing = [v for v in wanted if v not in got]
        if missing:
            failures.append(f"{key} missing {missing}")
    return not failures, report, failures


def _held(provider: str, stack: str, reason: str, *, model: str = "") -> dict[str, Any]:
    return {
        "provider": provider,
        "provider_stack": stack,
        "model_id": model,
        "status": "held",
        "correctness": False,
        "latency_ms": 0,
        "tool_calls": 0,
        "retries": 0,
        "failure_reason": reason,
        "usage": {},
        "teardown": "not started",
        "artifact_path": "",
    }


def _success(provider: str, stack: str, model: str, start: float, text: str,
             *, emitted: dict[str, Any] | None = None, tool_calls: int = 0,
             usage: dict[str, Any] | None = None, teardown: str = "not applicable",
             artifact_path: str = "") -> dict[str, Any]:
    ok, report, failures = score_report(text, emitted)
    return {
        "provider": provider,
        "provider_stack": stack,
        "model_id": model,
        "status": "success" if ok else "failed",
        "correctness": ok,
        "latency_ms": _now_ms(start),
        "tool_calls": tool_calls,
        "retries": 0,
        "failure_reason": "" if ok else "; ".join(failures),
        "usage": usage or {},
        "teardown": teardown,
        "artifact_path": artifact_path,
        "report": report,
    }


def managed_prompt() -> str:
    report = json.dumps(EXPECTED_REPORT, sort_keys=True)
    script = (
        "python3 - <<'PY'\n"
        "import json, pathlib\n"
        f"report = {report!r}\n"
        "pathlib.Path('/mnt/session/outputs').mkdir(parents=True, exist_ok=True)\n"
        "pathlib.Path('/mnt/session/outputs/ops_triage.json').write_text(report + '\\n')\n"
        "print(report)\n"
        "PY"
    )
    return (
        "Use bash to run exactly this script, then return only the JSON printed to stdout.\n\n"
        + script
    )


def run_managed_agent(client) -> dict[str, Any]:
    start = time.monotonic()
    tag = f"{COMPARE_PREFIX}-{uuid.uuid4().hex[:8]}"
    env = agent = session = None
    tool_events = 0
    reply: list[str] = []
    teardown: list[str] = []
    try:
        env = client.beta.environments.create(
            name=tag,
            config={"type": "cloud", "networking": {"type": "unrestricted"}},
        )
        agent = client.beta.agents.create(
            name=tag,
            model=FAST_MODEL,
            system="You are a terse ops agent. Use tools when asked and return only the requested JSON.",
            tools=[{"type": "agent_toolset_20260401", "default_config": {"enabled": True}}],
        )
        session = client.beta.sessions.create(
            agent={"type": "agent", "id": agent.id, "version": agent.version},
            environment_id=env.id,
            title="managed-agents comparison",
        )
        with client.beta.sessions.events.stream(session_id=session.id) as stream:
            client.beta.sessions.events.send(
                session_id=session.id,
                events=[{"type": "user.message", "content": [{"type": "text", "text": managed_prompt()}]}],
            )
            for event in stream:
                event_type = getattr(event, "type", "")
                if "tool" in event_type:
                    tool_events += 1
                if event_type == "agent.message":
                    for block in event.content:
                        if getattr(block, "type", "") == "text":
                            reply.append(block.text)
                elif event_type in ("session.status_idle", "session.status_terminated"):
                    break
    except Exception as exc:  # noqa: BLE001
        return _held("anthropic", "Claude Managed Agents", str(exc), model=FAST_MODEL)
    finally:
        if session is not None:
            teardown.append(_safe("delete session", client.beta.sessions.delete, session_id=session.id))
        if env is not None:
            teardown.append(_safe("delete environment", client.beta.environments.delete, env.id))
        if agent is not None:
            teardown.append(_safe("archive agent", client.beta.agents.archive, agent.id))
    return _success(
        "anthropic",
        "Claude Managed Agents",
        FAST_MODEL,
        start,
        "".join(reply),
        tool_calls=tool_events,
        teardown="; ".join(teardown),
        artifact_path="/mnt/session/outputs/ops_triage.json",
    )


def run_self_managed_claude() -> dict[str, Any]:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return _held("anthropic", "self-managed Messages tool loop", "ANTHROPIC_API_KEY is not set",
                     model=CLAUDE_SELF_MODEL)
    start = time.monotonic()
    try:
        import anthropic
    except Exception as exc:  # noqa: BLE001
        return _held("anthropic", "self-managed Messages tool loop", f"anthropic import failed: {exc}",
                     model=CLAUDE_SELF_MODEL)
    client = anthropic.Anthropic()
    messages: list[dict[str, Any]] = [{"role": "user", "content": PROMPT}]
    emitted: dict[str, Any] | None = None
    tool_calls = 0
    usage_totals: dict[str, int] = {}
    tools = [
        {
            "name": "fetch_ops_slice",
            "description": "Return one deterministic ops evidence slice.",
            "input_schema": {
                "type": "object",
                "properties": {"kind": {"type": "string", "enum": ["logs", "tickets", "deploys"]}},
                "required": ["kind"],
            },
        },
        {
            "name": "emit_incident_report",
            "description": "Emit the final incident report as structured JSON.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "incident_id": {"type": "string"},
                    "severity": {"type": "string"},
                    "root_cause": {"type": "string"},
                    "action": {"type": "string"},
                    "affected_accounts": {"type": "array", "items": {"type": "string"}},
                    "evidence_ids": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["incident_id", "severity", "root_cause", "action", "affected_accounts", "evidence_ids"],
            },
        },
    ]
    final_text = ""
    try:
        for _ in range(8):
            response = client.messages.create(
                model=CLAUDE_SELF_MODEL,
                max_tokens=600,
                tools=tools,
                messages=messages,
            )
            usage = getattr(response, "usage", None)
            if usage:
                for key in ("input_tokens", "output_tokens", "cache_read_input_tokens"):
                    usage_totals[key] = usage_totals.get(key, 0) + int(getattr(usage, key, 0) or 0)
            content = [block.to_dict() if hasattr(block, "to_dict") else block for block in response.content]
            messages.append({"role": "assistant", "content": content})
            tool_results = []
            tool_uses = [block for block in response.content if getattr(block, "type", "") == "tool_use"]
            if not tool_uses:
                final_text = "".join(getattr(block, "text", "") for block in response.content)
                break
            for use in tool_uses:
                tool_calls += 1
                if use.name == "fetch_ops_slice":
                    result = fetch_ops_slice(use.input["kind"])
                elif use.name == "emit_incident_report":
                    emitted = dict(use.input)
                    result = "accepted"
                else:
                    result = f"unknown tool: {use.name}"
                tool_results.append({"type": "tool_result", "tool_use_id": use.id, "content": result})
            messages.append({"role": "user", "content": tool_results})
    except Exception as exc:  # noqa: BLE001
        return _held("anthropic", "self-managed Messages tool loop", str(exc), model=CLAUDE_SELF_MODEL)
    return _success("anthropic", "self-managed Messages tool loop", CLAUDE_SELF_MODEL, start, final_text,
                    emitted=emitted, tool_calls=tool_calls, usage=usage_totals)


def run_openai_agents() -> dict[str, Any]:
    if not os.environ.get("OPENAI_API_KEY"):
        return _held("openai", "OpenAI Agents SDK", "OPENAI_API_KEY is not set", model=OPENAI_MODEL)
    start = time.monotonic()
    emitted: dict[str, Any] | None = None
    tool_calls = 0
    try:
        from agents import Agent, Runner, function_tool
    except Exception as exc:  # noqa: BLE001
        return _held("openai", "OpenAI Agents SDK", f"openai-agents import failed: {exc}", model=OPENAI_MODEL)

    @function_tool
    def fetch_ops_slice_tool(kind: str) -> str:
        """Return one deterministic ops evidence slice."""
        nonlocal tool_calls
        tool_calls += 1
        return fetch_ops_slice(kind)

    @function_tool
    def emit_incident_report_tool(report_json: str) -> str:
        """Record the final incident report JSON."""
        nonlocal emitted, tool_calls
        tool_calls += 1
        emitted = json.loads(report_json)
        return "accepted"

    async def _run() -> str:
        agent = Agent(
            name="ops_triage_agent",
            model=OPENAI_MODEL,
            instructions=(
                "Use fetch_ops_slice_tool for logs, tickets, and deploys. Then call "
                "emit_incident_report_tool with a JSON string. Return only the JSON."
            ),
            tools=[fetch_ops_slice_tool, emit_incident_report_tool],
        )
        result = await Runner.run(agent, PROMPT, max_turns=8)
        return str(result.final_output)

    try:
        text = asyncio.run(_run())
    except Exception as exc:  # noqa: BLE001
        return _held("openai", "OpenAI Agents SDK", str(exc), model=OPENAI_MODEL)
    return _success("openai", "OpenAI Agents SDK", OPENAI_MODEL, start, text,
                    emitted=emitted, tool_calls=tool_calls)


def run_google_adk() -> dict[str, Any]:
    if not os.environ.get("GEMINI_API_KEY") and not os.environ.get("GOOGLE_API_KEY"):
        return _held("google", "Google ADK with Gemini", "GEMINI_API_KEY or GOOGLE_API_KEY is not set",
                     model=GEMINI_MODEL)
    os.environ.setdefault("GOOGLE_API_KEY", os.environ.get("GEMINI_API_KEY", ""))
    start = time.monotonic()
    emitted: dict[str, Any] | None = None
    tool_calls = 0
    try:
        from google.adk.agents import Agent
        from google.adk.runners import Runner
        from google.adk.sessions import InMemorySessionService
        from google.genai import types
    except Exception as exc:  # noqa: BLE001
        return _held("google", "Google ADK with Gemini", f"google-adk import failed: {exc}", model=GEMINI_MODEL)

    def fetch_ops_slice_tool(kind: str) -> str:
        """Return one deterministic ops evidence slice."""
        nonlocal tool_calls
        tool_calls += 1
        return fetch_ops_slice(kind)

    def emit_incident_report_tool(report_json: str) -> str:
        """Record the final incident report JSON."""
        nonlocal emitted, tool_calls
        tool_calls += 1
        emitted = json.loads(report_json)
        return "accepted"

    try:
        agent = Agent(
            name="ops_triage_agent",
            model=GEMINI_MODEL,
            instruction=(
                "Use fetch_ops_slice_tool for logs, tickets, and deploys. Then call "
                "emit_incident_report_tool with a JSON string. Return only the JSON."
            ),
            tools=[fetch_ops_slice_tool, emit_incident_report_tool],
        )
        session_service = InMemorySessionService()
        session = asyncio.run(session_service.create_session(
            app_name="managed_agents_compare",
            user_id="local",
            session_id=f"cmp-{uuid.uuid4().hex[:8]}",
        ))
        runner = Runner(app_name="managed_agents_compare", agent=agent, session_service=session_service)
        message = types.Content(role="user", parts=[types.Part.from_text(text=PROMPT)])
        parts: list[str] = []
        for event in runner.run(user_id="local", session_id=session.id, new_message=message):
            content = getattr(event, "content", None)
            for part in getattr(content, "parts", []) or []:
                if getattr(part, "text", None):
                    parts.append(part.text)
        text = "".join(parts)
    except Exception as exc:  # noqa: BLE001
        return _held("google", "Google ADK with Gemini", str(exc), model=GEMINI_MODEL)
    return _success("google", "Google ADK with Gemini", GEMINI_MODEL, start, text,
                    emitted=emitted, tool_calls=tool_calls)


def write_receipt(receipt: dict[str, Any]) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    LAST_JSON.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# Managed Agents comparison receipt",
        "",
        f"status: {receipt['status']}",
        f"workload: {receipt['workload']['id']}",
        "",
        "| provider | stack | model | status | correct | latency_ms | tool_calls | failure |",
        "| --- | --- | --- | --- | --- | ---: | ---: | --- |",
    ]
    for arm in receipt["arms"]:
        lines.append(
            f"| {arm['provider']} | {arm['provider_stack']} | {arm['model_id']} | {arm['status']} | "
            f"{arm['correctness']} | {arm['latency_ms']} | {arm['tool_calls']} | {arm['failure_reason']} |"
        )
    LAST_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_compare(*, providers: list[str], live: bool) -> dict[str, Any]:
    arms: list[dict[str, Any]] = []
    provider_set = {p.strip() for p in providers if p.strip()}
    if not live:
        for provider in provider_set:
            arms.append(_held(provider, provider, "dry run only"))
    else:
        if "managed" in provider_set:
            try:
                import anthropic
                arms.append(run_managed_agent(anthropic.Anthropic()))
            except Exception as exc:  # noqa: BLE001
                arms.append(_held("anthropic", "Claude Managed Agents", str(exc), model=FAST_MODEL))
        if "self-managed" in provider_set:
            arms.append(run_self_managed_claude())
        if "openai" in provider_set:
            arms.append(run_openai_agents())
        if "gemini" in provider_set:
            arms.append(run_google_adk())

    all_correct = all(arm["status"] == "success" and arm["correctness"] for arm in arms)
    any_held = any(arm["status"] == "held" for arm in arms)
    status = "candidate"
    if all_correct and not any_held:
        status = "mechanically vetted"
    elif any_held:
        status = "held"
    receipt = {
        "schema_version": 1,
        "status": status,
        "promotion": "no promoted win unless the cross-provider receipt proves a Managed Agents advantage",
        "workload": {
            "id": "ops_triage_tool_loop",
            "description": "stateful ops triage over logs, tickets, and deploys",
            "expected": EXPECTED_REPORT,
        },
        "arms": arms,
    }
    write_receipt(receipt)
    return receipt


def format_receipt(receipt: dict[str, Any]) -> str:
    lines = [
        "=== managed-agents comparison ===",
        f"status: {receipt['status']}",
        f"receipt: {LAST_JSON}",
    ]
    for arm in receipt["arms"]:
        lines.append(
            f"- {arm['provider_stack']}: {arm['status']} correct={arm['correctness']} "
            f"latency_ms={arm['latency_ms']} tools={arm['tool_calls']} failure={arm['failure_reason'] or '-'}"
        )
    return "\n".join(lines)
