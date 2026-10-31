# 06 — Capstone: the defense (50 bonus points, human-graded)

The flags prove a chain ran. This final stage proves **you** understand it.
An AI can generate either; only one of them survives a live conversation
about its own work.

## Format

When you have 300+ points, book 45 minutes with a mentor (or two lab peers
grading each other with the rubric below). Bring your **derivation notebook**
(`work/notebook-template.md`) — raw notes, failed sweeps, leak parses, core
scans, every AI interaction logged per the honor code in `docs/05-ethics.md`.

The mentor picks 6 questions: two from each tier. You talk through YOUR
run — your numbers, your crashes, your dead ends.

## Question bank

### Tier 1 — mechanism (must be fluent)

1. Walk me through what PHP does between RINIT and your target script for a
   multipart POST. Where exactly does your OOM abort land, and why *there*?
2. Why does a form **field** exhaust memory_limit while a **file part** of
   the same size does not?
3. Your leak echoed ~4 KiB of heap in a header. What structure lied, and
   which field of it?
4. Why is a leaked pointer's low-12-bits page alignment a fingerprint? What
   does a decoy cluster get wrong?
5. Why do chunk bases defeat heap ASLR by masking 21 bits — and what would
   change if Zend used 4 MiB chunks?
6. Where does the per-boot layout shift come from, and why can't it move
   your stage-1 leak shape but does move your stage-3 address?

### Tier 2 — your run (answerable only if you did it)

7. Open your notebook to the first working leak. What N did you end up with,
   and what did the two failed sweeps before it look like?
8. Show me a decoy that fooled you. What made it plausible, and what
   eventually killed it?
9. What did your leak's pointer histogram actually look like? Sketch it.
10. Your libphp base was rejected once — why? (If it never was, explain what
    would cause that in a crowded boot.)
11. For the boss: what was your payload signature, and how close was your
    first constant guess?
12. What broke when the budget bit you mid-sweep, and what did you change?

### Tier 3 — transfer (the real exam)

13. The fix removes a session decode/encode from the parse window. Explain,
    from the mechanism, why that closes the leak channel and not merely the
    crash.
14. Why is FPM structurally unexploitable here even with an identical
    memory_limit config? Name the lifecycle difference.
15. You have a leak but no write on an ≤ 8.2 build. From the mechanism only,
    what changed in `php_session_send_cookie`, and what would you need to
    rebuild the channel?
16. If Zend MM switched to randomized size-class ordering per boot, which of
    your stages breaks first, and how would you adapt?
17. Design a detector: given only web-server logs, how would you distinguish
    a real exploitation attempt from a misconfigured client? Why is that
    boundary exactly where it is?
18. Your chain needs `memory_limit < 4 × post_max_size`. Invent a hardening
    that breaks the leak but not the application — and one that breaks the
    application too. Why do hardening guides usually get this wrong?

## Rubric (per tier: 0 / 1 / 2)

- **0** — recites the docs; cannot connect answers to their own artifacts.
- **1** — correct mechanism, hesitant on their own numbers.
- **2** — fluent, correct, and answers cite *their* artifacts unprompted.

30+ points of capstone requires 2s in tiers 1–2 and at least one 2 in
tier 3. A notebook with no failed attempts caps the capstone at 10 — dead
ends are evidence of work, not embarrassments.

## Why this stage exists

Everything else in this lab is verifiable by a machine, and a machine with
root can fake any of it. The capstone is graded the only way understanding
has ever been graded: by a human asking you to defend what you claim to know.
That is not a limitation of the lab; that is the point of it.
