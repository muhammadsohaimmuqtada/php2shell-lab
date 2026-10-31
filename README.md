# PHP2SHELL — Educational Exploitation Lab

**A self-contained, run-anywhere lab for learning heap exploitation on a real
PHP vulnerability class.** You get six intentionally vulnerable PHP servers
(five exploitable builds + one "research yard"), a scoring engine that
verifies your progress against **live process memory**, spoiler-gated hints,
and a boss fight whose key constant is deliberately not published anywhere.

```
 ██▓     ██▓ ▄████▄   ▒█████   ███▄    █  ▄▄▄█████▓▓█████  ██▀███  ▓█████
▓██▒    ▒▓██▒▒██▀ ▀█  ▒██▒  ██▒ ██▀▀█ █▒ ▓  ██▒ ▓▒▓█   ▀ ▓██ ▒ ██▒▓█   ▀
▒██░    ░▒██░▒▓█    ▄ ▒██░  ██▒▓██  ▒█░▒ ▒ ▓██░ ▒░▒███   ▓██ ░▄█ ▒▒███
▒██   ▒  ░██░▒▓▓▄ ▄██▒▒██   ██░▓██▒  ▐░▓ ▒░▓██░ ▒░▒▓█  ▄ ▒██▀▀█▄  ▒▓█  ▄
░ ████░ ░██░░ ▓███▀ ░░ ████▓▒░▒██░   ▓██░ ░▒██    ░░▒████▒░██▓ ▒██▒░▒████▒
```

| | |
|---|---|
| Vulnerability class | `memory_limit` exhaustion during multipart parse → dangling session state → heap leak → controlled function pointer |
| Targets | PHP 8.4.25 / 8.4.26 / 8.5.10 / 8.5.11 / **8.3.35 (boss)** / 8.1.34 (research yard) |
| Fixed in | 8.2.35 / 8.3.36 / 8.4.27 / 8.5.12 — **the builds here have no fixed release** |
| Prerequisites | Docker + Python 3.9+, nothing else |
| Points | 350 across 12 challenges, verified against the live worker |

> **This lab contains no exploit code.** You will build the chain yourself.
> Every stage you complete is verified against the real target — leaked
> pointers are checked against the running worker's `/proc/<pid>/maps`, and
> the final flag can only be read by code that actually executed inside the
> container.

---

## Quickstart

On your own machine (Docker required):

```bash
git clone <this repo> && cd php2shell-lab
./labctl doctor                  # environment check
./labctl start 8.4.25            # boot the tutorial build
curl -sI http://127.0.0.1:8081/ | grep -i powered
./labctl board                   # see the challenge ladder
open docs/03-lab-guide.md        # how to work the lab
```

No Docker locally? Open the repo in **GitHub Codespaces** — the included
`.devcontainer` ships docker-in-docker, so `./labctl` works unchanged in the
browser (all targets still bind to the Codespace's localhost).

When you believe you have completed a stage, submit it:

```bash
./labctl submit 8425 B1 0x7f3c20000000          # a leaked heap chunk base
./labctl submit 8425 B2 0x7f3c3a2b4000          # the libphp base
./labctl submit 8425 C1 $(cat flag.txt)         # contents of /flag
```

The checker tells you `ACCEPTED` or why your submission was rejected. Points
land on the local scoreboard (`./labctl board`, or `./labctl serve` for the
web view at `http://127.0.0.1:7777`).

## The ladder

| Track | Challenge | Build | Points | What you must demonstrate |
|---|---|---|---:|---|
| A — Recon | A1 `first-blood` | 8.4.25 | 15 | extract `zif_system` from the running worker's `libphp.so` |
| A — Recon | A2 `read-the-config` | any | 10 | read the effective `memory_limit` and `post_max_size` the SAPI really uses |
| B — Leak | B1 `chunk-zero` | 8.4.25 | 25 | defeat heap ASLR: leak a Zend MM chunk base |
| B — Leak | B2 `code-zero` | 8.4.25 | 25 | defeat PIE: leak the `libphp.so` load base |
| B — Leak | B3 `portable-leak` | 3 more builds | 25 | prove your leak generalizes (B1 on 8.4.26, 8.5.10, 8.5.11) |
| C — Execute | C1 `shell-on-8425` | 8.4.25 | 50 | code execution: read `/flag` |
| C — Execute | C2 `the-family` | 8.4.26 / 8.5.10 / 8.5.11 | 75 | RCE on all three remaining published-constant builds |
| C — Execute | **C3 `the-8.3-boss`** | **8.3.35** | **100** | RCE on a build whose payload address is published **nowhere** — derive it yourself |
| D — Research | D1 `corruption-yard` | 8.1.34 | 25 | trigger the startup-phase OOM marker on a build where the leak channel is severed |

Difficulty curve is deliberate: on the four "family" builds the payload
address inside the heap chunk is a **published public constant**
(`chunk + 0x690D8`, from the original research). On the boss build it is not
— you will have to find it with heap forensics (see `forensics/`).

## Why this vulnerability is worth learning

Request parsing happens **before any application code runs**. When a
`memory_limit` is exhausted mid-multipart-parse, PHP bails out leaving
session-upload-progress state dangling across an abort — and the next
request's data can land in the freed slot. That gap turns a data format into
a read primitive (a forged string length echoes 4 KiB of neighbouring heap
in a `Set-Cookie`), the read primitive into ASLR defeat, and ASLR defeat into
a controlled function-pointer write that fires at request shutdown.

The config class is everywhere: small `memory_limit` (8–32 M) plus a larger
`post_max_size` is a common shared-hosting misconfiguration, and the vulnerable
branch ≤ 8.1 **will never receive a fix**.

## Rules of engagement

1. Targets bind to `127.0.0.1` on your machine. Keep it that way.
2. Reading `/flag` via `docker exec` works (the checker does it) — but that
   is not exploitation and scores nothing. The scoreboard is for you.
3. Using an LLM as a *tutor* is encouraged; pasting the lab into one and
   asking for the flag is wasted money — the verified stages require live
   process state that no document in this repo contains.
4. Do not use anything you learn here against systems you do not own.

## Credits & provenance

Vulnerability research: **CVE-2026-109618 / CVE-2026-109619** (disclosed
2026-10-21; fixed in 8.2.35/8.3.36/8.4.27/8.5.12). Lab structure, scoring
engine, calibration notes and the boss-build constant derivation are from the
author's original engagement work. Upstream research that published the
8.4-era chain and the `chunk + 0x690D8` constant is credited in `docs/05-ethics.md`.

Everything runs on your hardware. No telemetry, no network calls except
Docker Hub image pulls.
