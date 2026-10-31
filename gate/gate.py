#!/usr/bin/env python3
"""php2shell-lab gate — the single entry point in front of every target.

Ports 8081-8086: BUDGETED mode. POST bodies >= 1 MiB are the OOM-probe
shape, and each boot allows a limited number of them (default 300). The
budget is what makes blind calibration sweeps uneconomical: an agent that
tries to search the spray space dies at the budget long before it finds the
shape, and a container restart re-randomizes the heap anyway. When the
budget is gone the gate answers 429 until `./labctl reset` (new boot, new
seed, new layout, fresh budget).

Ports 9081-9086: DIRECT mode (nightmare). No budget, straight to the
target — for crowded-worker practice once your tooling is already smart.

Everything forwards verbatim; the gate never rewrites bodies. Upstream
requests are sent with Connection: close and read to EOF (HTTP/1.0-style),
which keeps the relay trivial and bug-free at the cost of upstream
keep-alive — irrelevant in single-worker mode, and crowded mode exists
precisely to practice against direct ports.

Stats: GET /__lab/stats
"""
from __future__ import annotations

import json
import os
import select
import socket
import threading

LISTEN_MAP = {
    8081: ("web-8425", "budget"), 8082: ("web-8426", "budget"),
    8083: ("web-8510", "budget"), 8084: ("web-8511", "budget"),
    8085: ("web-8335", "budget"), 8086: ("web-8134", "budget"),
    9081: ("web-8425", "direct"), 9082: ("web-8426", "direct"),
    9083: ("web-8510", "direct"), 9084: ("web-8511", "direct"),
    9085: ("web-8335", "direct"), 9086: ("web-8134", "direct"),
}
BUDGET = int(os.environ.get("P2S_BUDGET", "300"))
BIG_BODY = 1 << 20
MAX_BODY = 64 << 20
MAX_UPSTREAM = 32 << 20

lock = threading.Lock()
counters = {host: {"oom_posts": 0, "total": 0, "budget": BUDGET}
            for host, _ in LISTEN_MAP.values()}


def read_request(conn) -> tuple[bytes, bytes, int] | None:
    """Read one request head + body. Returns (head, body, content_length)."""
    conn.settimeout(180)
    buf = b""
    while b"\r\n\r\n" not in buf:
        chunk = conn.recv(65536)
        if not chunk:
            return None
        buf += chunk
        if len(buf) > 65536:
            return None
    head, _, rest = buf.partition(b"\r\n\r\n")
    lines = head.split(b"\r\n")
    cl = 0
    for line in lines[1:]:
        if line.lower().startswith(b"content-length:"):
            try:
                cl = int(line.split(b":", 1)[1].strip())
            except ValueError:
                cl = 0
    if cl > MAX_BODY:
        return None
    body = rest
    while len(body) < cl:
        chunk = conn.recv(min(1 << 20, cl - len(body)))
        if not chunk:
            break
        body += chunk
    return head, body[:cl], cl


def forward(host: str, head: bytes, body: bytes) -> bytes:
    """Send upstream with Connection: close, read response to EOF."""
    s = socket.create_connection((host, 80), timeout=300)
    try:
        lines = head.split(b"\r\n")
        out = [lines[0]]
        for line in lines[1:]:
            low = line.lower()
            if low.startswith(b"connection:") or low.startswith(b"expect:") \
                    or low.startswith(b"keep-alive:") or low.startswith(b"proxy-"):
                continue
            out.append(line)
        out.append(b"Connection: close")
        s.sendall(b"\r\n".join(out) + b"\r\n\r\n" + body)
        resp = b""
        while len(resp) < MAX_UPSTREAM:
            chunk = s.recv(1 << 20)
            if not chunk:
                break
            resp += chunk
        return resp
    finally:
        s.close()


class Handler(threading.Thread):
    def __init__(self, conn, port):
        super().__init__(daemon=True)
        self.conn = conn
        self.port = port

    def run(self):
        try:
            self.handle()
        except OSError:
            pass
        finally:
            try:
                self.conn.close()
            except OSError:
                pass

    def handle(self):
        host, mode = LISTEN_MAP[self.port]
        req = read_request(self.conn)
        if req is None:
            return
        head, body, cl = req

        if head.startswith(b"GET /__lab/stats"):
            with lock:
                payload = json.dumps({"gate": {"budget": BUDGET},
                                      "targets": counters}, indent=2)
            body_out = payload.encode()
            self.conn.sendall(
                b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n"
                b"Content-Length: " + str(len(body_out)).encode()
                + b"\r\nConnection: close\r\n\r\n" + body_out)
            return

        with lock:
            counters[host]["total"] += 1
            if mode == "budget" and cl >= BIG_BODY:
                counters[host]["oom_posts"] += 1
                exhausted = counters[host]["oom_posts"] > counters[host]["budget"]
            else:
                exhausted = False

        if exhausted:
            msg = (b"lab attempt budget exhausted for this boot.\n"
                   b"Blind sweeps will not beat per-boot randomization.\n"
                   b"./labctl reset  ->  new seed, new layout, fresh budget.\n")
            self.conn.sendall(
                b"HTTP/1.1 429 Too Many Requests\r\n"
                b"Content-Type: text/plain\r\nConnection: close\r\n\r\n" + msg)
            return

        resp = forward(host, head, body)
        self.conn.sendall(resp)


def main():
    servers = []
    for port in LISTEN_MAP:
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind(("0.0.0.0", port))
        srv.listen(128)
        servers.append(srv)
        print(f"[gate] :{port} -> {LISTEN_MAP[port][0]} ({LISTEN_MAP[port][1]})",
              flush=True)
    print(f"[gate] OOM-probe budget per boot: {BUDGET}", flush=True)
    conns, wlist = [], servers
    while True:
        rlist, _, _ = select.select(wlist, [], [], 1.0)
        for s in rlist:
            try:
                conn, _ = s.accept()
            except OSError:
                continue
            Handler(conn, s.getsockname()[1]).start()


if __name__ == "__main__":
    main()
