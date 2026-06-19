#!/usr/bin/env python3
"""Stop hook: ask Claude to run verification before it stops, if it hasn't already.

"Already" means the receipt at data/last_run.md was refreshed recently, which a live run does on
every run. If it is stale or missing, block the stop once with a reason pointing at the verify
skill. Once `python run.py` has run, the receipt is fresh and the hook lets the agent stop, so it
nudges without looping forever.
"""

import json
import sys
import time
from pathlib import Path

RECEIPT = Path(__file__).resolve().parents[2] / "data" / "last_run.md"
FRESH_SECONDS = 30 * 60


def main():
    try:
        json.load(sys.stdin)  # the Stop hook payload; the decision here does not need its fields
    except Exception:
        pass

    fresh = RECEIPT.exists() and (time.time() - RECEIPT.stat().st_mtime) < FRESH_SECONDS
    if fresh:
        sys.exit(0)  # verification ran recently, let the agent stop

    print(
        json.dumps(
            {
                "decision": "block",
                "reason": (
                    "Run the verify skill before stopping: `python run.py`, then the offline gates "
                    "(`python scripts/deslop_check.py`, compileall, unittest). "
                    "The receipt at data/last_run.md is stale or missing."
                ),
            }
        )
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
