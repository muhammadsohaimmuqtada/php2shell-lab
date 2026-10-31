# Challenge ladder — 350 points

Submit with `./labctl submit <version> <ID> <value>`. Every stage is
verified against the live container. Hints: `./labctl hint <ID> <1-3>`
(level 3 is as far as the lab will ever go).

> **Every boot is a new instance.** The `p2slab` extension shifts the request
> heap by a seed-derived delta, plants a fresh 16-byte canary, and scatters
> decoy pointer clusters. Bases are per-boot; constants do not carry across
> restarts; statistical shortcuts verify against decoys. The gate enforces
> an OOM-probe budget per boot (`./labctl budget`) — sweeps are uneconomical
> by design.

---

## Track A — Recon (25 pts)

### A1 · first-blood — 15 pts · target `8.4.25`
Extract the `zif_system` module offset from the running worker's
`libphp.so`. Submit the offset (e.g. `0x43a870`).
*Verified against the container's actual binary.*

### A2 · read-the-config — 10 pts · target `8.4.25`
Read the **effective** `memory_limit` and `post_max_size` as the SAPI sees
them. Submit both, comma-separated (e.g. `128M,8M` — not this lab's values).
*Verified against `php -i` inside the container.*

---

## Track B — Leak (75 pts)

### B1 · chunk-zero — 25 pts · targets `8.4.25 8.4.26 8.5.10 8.5.11 8.3.35`
Leak a Zend MM chunk base from the worker's heap and submit it
(`0x7f3c20000000`). *Verified: 2 MiB-aligned, inside a live worker's
anonymous rw arena.*

### B2 · code-zero — 25 pts · same targets
Leak the `libphp.so` load base **and this boot's canary** — the 16 bytes
following the `P2SLABCB` magic in the leak window. Submit
`libphp_base,canary`. *Verified: base equals the live load base in
`/proc/<worker>/maps`, canary matches this boot's seed — a copied or
out-of-band answer fails.*

### B3 · portable-leak — 25 pts
Repeat B1 on **8.4.26, 8.5.10, 8.5.11**. Submit three comma-separated chunk
bases in that order. Prereq: B1.

---

## Track C — Execute (225 pts)

### C1 · shell-on-8425 — 50 pts · target `8.4.25`
Full chain: read `/flag` from inside the container with code you executed
through the request lifecycle. Submit the 32-hex flag. Prereqs: B1, B2.

### C2 · the-family — 75 pts
Three flags, comma-separated: `8.4.26, 8.5.10, 8.5.11`. The payload address
for these builds is published research (`chunk + 0x690D8`). Prereqs: B3, C1.

### C3 · the-8.3-boss — 100 pts · target `8.3.35`
RCE on 8.3.35. **No published constant exists for this build** — the 8.4-era
`0x690D8` does not apply (pre-`extra_flags` layout). Derive the real address
with heap forensics (`forensics/README.md`): crash the worker, scan the chunk
for your own payload signature, compute the offset. Prereqs: B1+B2 on 8335.

---

## Track D — Research yard (25 pts)

### D1 · corruption-yard — 25 pts · target `8.1.34`
Prove the corruption fires on a build where the leak channel is severed.
Capture the parse-window fatal (`in Unknown on line 0`) and submit the
integer N from `tried to allocate N bytes`. This is why the EOL corpus —
85% of the measured vulnerable population — can never be remotely patched:
no fix exists, and the remote read primitive does not exist either.

---

## Scoring notes

- Rejected submissions never cost points.
- `--crowded` mode does not change scoring — it changes how hard C1/C3 are
  to land.
- The scoreboard is local (`./labctl board` / `./labctl serve`). 350/350
  means you independently reproduced a published chain, ported it across
  three builds, derived an unpublished constant from a core dump, and
  characterized an unfixable branch. That is a real research skillset.
