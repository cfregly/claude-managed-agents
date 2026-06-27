#!/usr/bin/env python3
"""One-command entry for the Managed Agents live smoke. Online only.

    ANTHROPIC_API_KEY=... python run.py            # provision env + agent + session, run one turn, tear down
    ANTHROPIC_API_KEY=... python run.py --cleanup  # sweep leftover smoke resources from a failed run
    ANTHROPIC_API_KEY=... OPENAI_API_KEY=... GEMINI_API_KEY=... python run.py compare --live

Requires ANTHROPIC_API_KEY and the Managed Agents beta on your org. The default smoke calls the
real API. Without a key it fails fast with a clear error and a non-zero exit. The eleven surfaces are
documented in the README. The compare mode has a dry path and a live provider path. After a run it
writes a receipt to data/last_run.md, which the Stop hook checks before it lets an agent stop.
"""

import argparse
import sys
from pathlib import Path

from managed_agents.client import get_client, require_key
from managed_agents.live import cleanup, live_smoke

RECEIPT = Path(__file__).resolve().parent / "data" / "last_run.md"


def _write_receipt(label):
    RECEIPT.parent.mkdir(parents=True, exist_ok=True)
    RECEIPT.write_text(f"# last run\n\n{label}\n")


def parse_args(argv):
    parser = argparse.ArgumentParser(
        prog="run",
        description="Run the Managed Agents live smoke or cleanup sweep.",
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="sweep leftover smoke resources from a failed run",
    )
    subparsers = parser.add_subparsers(dest="command")
    compare = subparsers.add_parser("compare", help="compare Managed Agents with other agent stacks")
    compare.add_argument("--live", action="store_true", help="run live provider arms")
    compare.add_argument(
        "--providers",
        default="managed,self-managed,openai,gemini",
        help="comma-separated provider arms: managed,self-managed,openai,gemini",
    )
    compare.add_argument(
        "--check",
        action="store_true",
        help="return non-zero unless every requested live arm succeeds",
    )
    return parser.parse_args(argv)


def main(argv):
    args = parse_args(argv)
    if args.command == "compare":
        from managed_agents.compare import format_receipt, run_compare

        receipt = run_compare(
            providers=args.providers.split(","),
            live=args.live,
        )
        print(format_receipt(receipt))
        _write_receipt("ran: comparison harness")
        if args.check and receipt["status"] != "mechanically vetted":
            return 1
        return 0

    try:
        require_key()
    except RuntimeError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    client = get_client()

    if args.cleanup:
        print("=== cleanup: sweep leftover claude-managed-agents-smoke resources ===")
        print(cleanup(client))
        _write_receipt("ran: cleanup sweep")
        return 0

    print("=== live end-to-end: environment -> agent -> session -> one turn -> teardown ===")
    print(live_smoke(client))
    _write_receipt("ran: live end-to-end smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
