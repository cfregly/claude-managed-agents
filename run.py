#!/usr/bin/env python3
"""One-command entry for the Managed Agents surface tour.

    python run.py                 # offline: every surface, as a dry run of its request shape
    python run.py memory_store    # one surface, dry run
    python run.py --live          # provision a real env + agent + session, run one turn, tear down

Default is the offline dry run, so no run provisions a real resource by accident. --live needs
ANTHROPIC_API_KEY and the Managed Agents beta enabled on your org. After a run it writes a short
receipt to data/last_run.md, which the Stop hook checks before it lets an agent stop.
"""

import sys
from pathlib import Path

from managed_agents.client import get_client, key_present
from managed_agents.live import live_smoke
from managed_agents.surfaces import REGISTRY

RECEIPT = Path(__file__).resolve().parent / "data" / "last_run.md"


def _names(argv):
    return [a for a in argv if not a.startswith("-")]


def _write_receipt(label, mode):
    RECEIPT.parent.mkdir(parents=True, exist_ok=True)
    RECEIPT.write_text(f"# last run\n\nmode: {mode}\n{label}\n")


def main(argv):
    live = "--live" in argv
    names = _names(argv)

    if live:
        if not key_present():
            print("--live needs ANTHROPIC_API_KEY and the Managed Agents beta on your org.")
            print("Run `python run.py` for the offline surface tour.")
            return 2
        client = get_client(live=True)
        print("=== live end-to-end: environment -> agent -> session -> one turn -> teardown ===")
        print(live_smoke(client))
        _write_receipt("ran: live end-to-end smoke", "live")
        return 0

    if names:
        unknown = [n for n in names if n not in REGISTRY]
        if unknown:
            print("unknown surface(s): " + ", ".join(unknown))
            print("available: " + ", ".join(REGISTRY))
            return 2
        selected = names
    else:
        selected = list(REGISTRY)

    for name in selected:
        summary, fn = REGISTRY[name]
        print(f"\n=== {name}  ({summary})  [dry] ===")
        print(fn(None))

    _write_receipt(f"surfaces: {len(selected)}", "dry")
    print(f"\nshowed {len(selected)} surface(s) in dry mode. receipt: data/last_run.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
