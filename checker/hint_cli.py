#!/usr/bin/env python3
"""./labctl hint <ID> <level> — prints one hint level, nothing more."""
import sys
from hints import HINTS

def main() -> int:
    if len(sys.argv) != 3 or sys.argv[2] not in ("1", "2", "3"):
        print("usage: labctl hint <ID> <1-3>")
        return 2
    cid, lvl = sys.argv[1].upper(), int(sys.argv[2])
    if cid not in HINTS:
        print(f"no hints for {cid!r}")
        return 2
    print(f"--- {cid} hint level {lvl}/3 ---")
    print(HINTS[cid][lvl - 1])
    return 0

if __name__ == "__main__":
    sys.exit(main())
