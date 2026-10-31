#!/usr/bin/env python3
"""php2shell lab — scoring engine.

    python3 checker/score.py list
    python3 checker/score.py submit <version> <challenge> <value>
    python3 checker/score.py board
    python3 checker/score.py serve [port]

State lives in .lab/score.json next to this repo's root.
"""
from __future__ import annotations

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify as V  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE = os.path.join(ROOT, ".lab", "score.json")

# id, title, points, versions, verifier, prerequisites (same-version unless noted)
CHALLENGES = {
    "A1": dict(title="first-blood: extract zif_system", points=15, versions=["8.4.25"],
               verifier="zif", prereq=[]),
    "A2": dict(title="read-the-config: effective memory_limit,post_max_size",
               points=10, versions=["8.4.25"], verifier="config", prereq=[]),
    "B1": dict(title="chunk-zero: leak a Zend MM chunk base", points=25,
               versions=["8.4.25", "8.4.26", "8.5.10", "8.5.11", "8.3.35"],
               verifier="chunk", prereq=["A1"]),
    "B2": dict(title="code-zero: leak the libphp.so load base", points=25,
               versions=["8.4.25", "8.4.26", "8.5.10", "8.5.11", "8.3.35"],
               verifier="libphp", prereq=["B1"]),
    "B3": dict(title="portable-leak: chunk bases for 8426,8510,8511 (comma-sep)",
               points=25, versions=["8.4.25"], verifier="chunk3", prereq=["B1"]),
    "C1": dict(title="shell-on-8425: read /flag via code execution", points=50,
               versions=["8.4.25"], verifier="flag", prereq=["B1", "B2"]),
    "C2": dict(title="the-family: /flag from 8426,8510,8511 (comma-sep)", points=75,
               versions=["8.4.25"], verifier="flag3", prereq=["B3", "C1"]),
    "C3": dict(title="the-8.3-boss: RCE on 8.3.35 (unpublished constant)", points=100,
               versions=["8.3.35"], verifier="flag", prereq=["B1", "B2"]),
    "D1": dict(title="corruption-yard: OOM abort size N on 8.1.34", points=25,
               versions=["8.1.34"], verifier="oom", prereq=[]),
}

VERIFIER = {
    "zif": lambda v, x: V.check_zif(v, int(x, 0)),
    "config": V.check_config,
    "chunk": lambda v, x: V.check_chunk(v, int(x, 0)),
    "libphp": lambda v, x: V.check_libphp(v, int(x, 0)),
    "flag": V.check_flag,
    "oom": lambda v, x: V.check_oom_n(x),
}

VERSION_ALIASES = {v.replace(".", ""): v for v in V.CONTAINERS}


def norm_version(v: str) -> str:
    return VERSION_ALIASES.get(v.replace(".", ""), v)


def load_state() -> dict:
    if os.path.exists(STATE):
        with open(STATE, encoding="utf-8") as fh:
            return json.load(fh)
    return {}


def save_state(st: dict) -> None:
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    with open(STATE, "w", encoding="utf-8") as fh:
        json.dump(st, fh, indent=2, sort_keys=True)


def challenge_done(st: dict, version: str, cid: str) -> bool:
    return cid in st.get(version, {})


def cmd_submit(version: str, cid: str, value: str) -> int:
    version = norm_version(version)
    chal = CHALLENGES.get(cid)
    if chal is None:
        print(f"unknown challenge {cid!r} — see `score.py list`")
        return 2
    if version not in chal["versions"]:
        print(f"{cid} is assessed on {'/'.join(chal['versions'])}, not {version}")
        return 2
    st = load_state()
    if challenge_done(st, version, cid):
        rec = st[version][cid]
        print(f"already accepted ({rec['points']} pts): {rec['detail']}")
        return 0
    for pre in chal["prereq"]:
        # B3/C2 are recorded under the tutorial build regardless of target
        pre_v = "8.4.25" if pre in ("B3", "C2") else version
        if not challenge_done(st, pre_v, pre):
            print(f"locked: complete {pre} on {pre_v} first "
                  f"({CHALLENGES[pre]['title']})")
            return 2

    fname = chal["verifier"]
    if fname == "chunk3":
        parts = [p.strip() for p in value.split(",") if p.strip()]
        if len(parts) != 3:
            print("submit three comma-separated chunk bases: 8426,8510,8511")
            return 2
        results = [V.check_chunk(v, int(x, 0))
                   for v, x in zip(["8.4.26", "8.5.10", "8.5.11"], parts)]
    elif fname == "flag3":
        parts = [p.strip() for p in value.split(",") if p.strip()]
        if len(parts) != 3:
            print("submit three comma-separated flags: 8426,8510,8511")
            return 2
        results = [V.check_flag(v, x)
                   for v, x in zip(["8.4.26", "8.5.10", "8.5.11"], parts)]
    else:
        try:
            results = [VERIFIER[fname](version, value)]
        except V.VerifyError as exc:
            print(f"checker error: {exc}")
            return 2
        except (ValueError, TypeError) as exc:
            print(f"cannot parse value: {exc}")
            return 2

    ok = all(r[0] for r in results)
    detail = " | ".join(r[1] for r in results)
    if ok:
        st.setdefault(version, {})[cid] = {"points": chal["points"], "detail": detail}
        save_state(st)
        print(f"ACCEPTED  +{chal['points']} pts  [{version}/{cid}]  {detail}")
        print(f"total: {total(st)} / 350")
    else:
        print(f"REJECTED  [{version}/{cid}]  {detail}")
    return 0 if ok else 1


def total(st: dict) -> int:
    return sum(rec["points"] for v in st.values() for rec in v.values())


def cmd_board() -> None:
    st = load_state()
    print(f"{'ver':7} {'id':3} {'pts':>4}  title")
    print("-" * 72)
    for cid, chal in CHALLENGES.items():
        for ver in chal["versions"]:
            rec = st.get(ver, {}).get(cid)
            mark = f"{rec['points']:>4} ✓" if rec else "   ·"
            print(f"{ver:7} {cid:3} {mark}  {chal['title']}")
    print("-" * 72)
    print(f"total: {total(st)} / 350")


def render_board_html() -> str:
    st = load_state()
    rows = []
    for cid, chal in CHALLENGES.items():
        for ver in chal["versions"]:
            rec = st.get(ver, {}).get(cid)
            cls = "done" if rec else ""
            rows.append(
                f"<tr class='{cls}'><td>{ver}</td><td>{cid}</td>"
                f"<td>{chal['title']}</td><td>{chal['points']}</td>"
                f"<td>{rec['points'] if rec else '—'}</td></tr>")
    pct = int(total(st) / 350 * 100)
    return f"""<!doctype html><html><head><meta charset="utf-8">
<title>php2shell lab — scoreboard</title><style>
body{{background:#0d1117;color:#e6edf3;font:15px/1.5 ui-monospace,Menlo,monospace;margin:0}}
header{{padding:22px 28px;border-bottom:1px solid #30363d}}
h1{{margin:0;font-size:1.3rem}}h1 span{{color:#f78166}}
.bar{{height:10px;background:#161b22;border:1px solid #30363d;border-radius:5px;margin:14px 0}}
.bar i{{display:block;height:100%;background:#3fb950;border-radius:5px;width:{pct}%}}
table{{border-collapse:collapse;width:100%;max-width:900px;margin:24px auto}}
td,th{{padding:7px 12px;border-bottom:1px solid #21262d;text-align:left}}
tr.done td{{color:#3fb950}}th{{color:#8b949e;font-weight:600}}
footer{{text-align:center;color:#8b949e;padding:18px}}
</style></head><body>
<header><h1>PHP2SHELL<span> // LAB</span> scoreboard</h1>
<div class="bar"><i></i></div><small>{total(st)} / 350 pts — {pct}%</small></header>
<table><tr><th>build</th><th>id</th><th>challenge</th><th>max</th><th>scored</th></tr>
{''.join(rows)}</table>
<footer>local only · targets on 127.0.0.1 · verified against live process memory</footer>
</body></html>"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = render_board_html().encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    cmd = sys.argv[1]
    if cmd == "list":
        for cid, chal in CHALLENGES.items():
            print(f"{cid:3} {chal['points']:>4} pts  {'/'.join(chal['versions']):20} {chal['title']}")
        return 0
    if cmd == "submit":
        if len(sys.argv) != 5:
            print("usage: score.py submit <version> <challenge> <value>")
            return 2
        return cmd_submit(sys.argv[2], sys.argv[3], sys.argv[4])
    if cmd == "board":
        cmd_board()
        return 0
    if cmd == "serve":
        port = int(sys.argv[2]) if len(sys.argv) > 2 else 7777
        print(f"scoreboard on http://127.0.0.1:{port} (Ctrl-C to stop)")
        HTTPServer(("127.0.0.1", port), Handler).serve_forever()
        return 0
    print(f"unknown command {cmd!r}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
