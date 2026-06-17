#!/usr/bin/env python3
"""One-command entry for the Managed Agents live smoke. Online only.

    ANTHROPIC_API_KEY=... python run.py            # provision env + agent + session, run one turn, tear down
    ANTHROPIC_API_KEY=... python run.py --cleanup  # sweep leftover smoke resources from a failed run

Requires ANTHROPIC_API_KEY and the Managed Agents beta on your org. Every run calls the real API.
Without a key it fails fast with a clear error and a non-zero exit. There is no offline mode. The
eleven surfaces are documented in the README; this script runs the real end-to-end smoke. After a
run it writes a receipt to data/last_run.md, which the Stop hook checks before it lets an agent stop.
"""

import sys
from pathlib import Path

from managed_agents.client import get_client, require_key
from managed_agents.live import cleanup, live_smoke

RECEIPT = Path(__file__).resolve().parent / "data" / "last_run.md"


def _write_receipt(label):
    RECEIPT.parent.mkdir(parents=True, exist_ok=True)
    RECEIPT.write_text(f"# last run\n\n{label}\n")


def main(argv):
    try:
        require_key()
    except RuntimeError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    client = get_client()

    if "--cleanup" in argv:
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
