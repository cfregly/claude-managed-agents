"""A small deslop gate: the prose docs state facts in plain language.

No em-dashes, no en-dashes, no semicolons in the README or CLAUDE.md. Self-contained, no
dependency, so CI runs it offline. Exits non-zero on a hit.
"""

import pathlib
import sys

BANNED = {"—": "em-dash", "–": "en-dash", ";": "semicolon"}
ROOT = pathlib.Path(__file__).resolve().parent.parent


def main():
    bad = []
    for name in ("README.md", "CLAUDE.md"):
        text = (ROOT / name).read_text()
        for i, line in enumerate(text.splitlines(), 1):
            for ch, label in BANNED.items():
                if ch in line:
                    bad.append(f"{name}:{i}: {label}")
    if bad:
        print("deslop gate: FAIL")
        print("\n".join(bad))
        sys.exit(1)
    print("deslop gate: clean")


if __name__ == "__main__":
    main()
