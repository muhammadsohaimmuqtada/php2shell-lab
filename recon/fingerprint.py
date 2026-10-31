#!/usr/bin/env python3
"""recon/fingerprint.py — what build is this, and what config class?

    python3 recon/fingerprint.py 8.4.25
"""
from __future__ import annotations

import re
import subprocess
import sys
import urllib.request

sys.path.insert(0, __import__("os").path.join(__import__("os").path.dirname(__file__), "..", "checker"))
from verify import CONTAINERS  # noqa: E402

PORTS = {"8.4.25": 8081, "8.4.26": 8082, "8.5.10": 8083,
         "8.5.11": 8084, "8.3.35": 8085, "8.1.34": 8086}


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    version = sys.argv[1]
    name = CONTAINERS[version]
    port = PORTS[version]

    req = urllib.request.Request(f"http://127.0.0.1:{port}/")
    with urllib.request.urlopen(req, timeout=5) as r:
        powered = r.headers.get("X-Powered-By", "?")
    print(f"[+] banner   : {powered}")

    ini = subprocess.run(["docker", "exec", name, "php", "-i"],
                         capture_output=True, text=True).stdout
    for key in ("memory_limit", "post_max_size", "display_errors",
                "session.upload_progress.enabled"):
        m = re.search(rf"(?m)^{re.escape(key)}\s*=>\s*(\S+)\s*=>", ini)
        print(f"[+] {key:36} {m.group(1) if m else '?'}")

    workers = subprocess.run(
        ["docker", "exec", name, "ps", "-eo", "args"],
        capture_output=True, text=True).stdout.count("apache2")
    print(f"[+] apache processes    : {workers} (1 = parent, others = workers)")
    print("[!] fixed-in: 8.2.35 / 8.3.36 / 8.4.27 / 8.5.12 — this build predates")
    return 0


if __name__ == "__main__":
    sys.exit(main())
