# 03 — Lab guide

## 0. Mindset

The lab gives you: vulnerable servers, recon tools, a verifier, and hints.
It does **not** give you: an exploit, calibrated spray shapes, or the
boss-build payload address. Expect the B track to take an evening and the C3
boss a second one. That is the design — a chain you assembled yourself is
worth ten you copied.

## 1. Workflow

```bash
./labctl doctor
./labctl start 8.4.25          # tutorial build, port 8081
python3 recon/fingerprint.py 8.4.25
python3 recon/symbols.py 8.4.25
./labctl submit 8425 A1 0x...  # whatever symbols.py prints — first blood
```

Work in your own directory (`work/`, gitignored). Keep notes: the leak
parsing you write for B1 is reused five times.

## 2. Submission protocol

Every stage is verified against the live container:

- `A1` — your zif offset must equal the real symbol offset.
- `B1` — your chunk base must be a 2 MiB-aligned address inside a large
  anonymous rw mapping of a **currently running** worker.
- `B2` — your libphp base must equal the live load base from
  `/proc/<worker>/maps`.
- `C*` — your flag must match `/flag` minted at container start.
- Rejections tell you *why* without leaking the answer.

If a submission fails after a genuine success, the worker probably rotated
(singleton mode: it does not; crowded mode: it does) — re-leak and resubmit.

## 3. Modes

- **single** (default): one worker, deterministic heap — learn here, on the
  budgeted ports 808x.
- **`--crowded`** (nightmare): 25 workers, keep-alive on, **direct ports
  908x** (no attempt budget). The aborting worker and the next request must
  be the same process; connection pinning becomes part of the exploit.

```bash
./labctl stop 8.4.25 && ./labctl start 8.4.25 --crowded
```

## 3b. The gate and the attempt budget

All standard traffic goes through the gate (808x). POST bodies of 1 MiB or
more are the OOM-probe shape and count against a per-boot budget (default
300, `./labctl budget` to see it live). Over budget: 429 until
`./labctl reset` — which also re-randomizes the heap, so a budget reset
never preserves your measurements. This is deliberate: calibration by
brute-force sweep must cost more than calibration by understanding.

## 3c. Exam mode

`./labctl exam on` — rejections carry no reason and submissions throttle to
one per 10 s. Use it when your tooling works and you want to be graded the
way the capstone will grade you: no oracle, just judgment. `./labctl exam
off` restores full feedback.

## 4. Suggested order

1. A1, A2 — warm up the toolchain.
2. B1 on 8.4.25 — the read primitive. Hardest single step of the family.
3. B2, C1 — finish the published-constant build end to end.
4. B3 + C2 — port to 8.4.26 / 8.5.10 / 8.5.11 (mechanism identical).
5. C3 — the boss: derive 8.3.35's constant with `forensics/`.
6. D1 — the research yard: see why ≤ 8.2 cannot leak remotely.

## 5. Debugging hygiene

- `docker logs p2slab-8425` shows Apache's side: segfaults (`signal 11`),
  child respawns, your OOM fatals.
- The container's `/tmp` holds session state — inspect it between requests.
- Keep the target's PHP version in mind when reading crash output: 8.4+
  objects carry `extra_flags`, shifting every later allocation.

## 6. Reset

`./labctl reset` removes containers, volumes, and your score. The score is
local; there is no server to cheat and no leaderboard to impress.
