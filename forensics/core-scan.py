#!/usr/bin/env python3
"""forensics/core-scan.py — locate your payload signature inside a core dump
(or any memory snapshot), relative to a known Zend chunk base.

    python3 forensics/core-scan.py <core-file> --chunk 0x7f3c20000000 --sig P2SBOSS1
    python3 forensics/core-scan.py <core-file> --chunk 0x... --sig P2SBOSS1 --span 0x400000
"""
from __future__ import annotations

import argparse
import mmap
import re
import sys


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("core")
    ap.add_argument("--chunk", required=True, help="chunk base from your B1 leak")
    ap.add_argument("--sig", required=True, help="marker string you planted")
    ap.add_argument("--span", type=lambda x: int(x, 0), default=1 << 21,
                    help="bytes to scan from chunk base (default 2 MiB)")
    args = ap.parse_args()

    base = int(args.chunk, 0)
    pat = args.sig.encode()
    with open(args.core, "rb") as fh:
        mm = mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ)
        # search the whole core once, then report hits within [base, base+span)
        hits = [m.start() for m in re.finditer(re.escape(pat), mm)]
    if not hits:
        print("signature not found — wrong marker, or the payload never landed")
        return 1
    in_region = 0
    for h in sorted(hits):
        # The core's file offsets need not equal virtual addresses; for Zend
        # chunk scanning the delta is constant per mapping, so print the hit
        # offsets relative to the FIRST occurrence candidate of the chunk in
        # file space. Practical mode: also try to find the chunk bytes directly.
        pass
    # Practical approach: locate the chunk inside the core by scanning for
    # 2MiB-aligned candidate offsets whose relative layout matches: we cannot
    # know VA layout without ELF notes, so we report FILE offsets and the
    # nearest 2MiB-aligned anchor.
    anchors = sorted({h & ~0x1FFFFF for h in hits})
    print(f"signature hits: {len(hits)} total")
    for a in anchors[:8]:
        rel = [h - a for h in hits if a <= h < a + args.span]
        print(f"  file-anchor {hex(a)}: hits at +{[hex(x) for x in rel]}")
    print("\nnote: file offsets != virtual addresses; if your core has a clean")
    print("VA mapping (gcore), file offset == virtual offset for the heap and")
    print("constant = (hit - chunk_base). Compute it, subtract your marker's")
    print("offset within the fake structure, and you have the payload address.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
