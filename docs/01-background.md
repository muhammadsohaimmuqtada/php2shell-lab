# 01 — Background: what runs before your code

To exploit this class you need a precise mental model of three PHP internals.
Thirty minutes here saves days of blind fuzzing later.

## 1. The request lifecycle

```
SAPI startup (mod_php: once per worker process)
  MINIT  — engine + extensions initialize
request:
  RINIT  — per request: $_SESSION decode, INI per-dir, ... 
  PARSE  — multipart/form-data bodies are parsed HERE, before any script
  script runs (your index.php)
  RSHUTDOWN — session close, upload-progress cleanup, output flush
shutdown:
  MSHUTDOWN — once per worker lifetime
```

The exploit-relevant fact: **the multipart parse runs in the window between
RINIT and script execution.** The application cannot defend, log, or even
observe what happens there. `in Unknown on line 0` in a fatal error is the
signature of a failure in that pre-script window — no script was on the line.

## 2. Zend MM — the allocator your spray talks to

PHP does not `malloc` per zval. It manages memory in **2 MiB chunks**, carved
into pages of 4 KiB, served through size-class **bins**. Two consequences:

- **Determinism.** Same request shape → same allocation sequence → same
  slots. Heap grooming is engineering, not luck.
- **Alignment.** Every chunk starts at a 2 MiB boundary, so a leaked pointer
  reveals the chunk base by masking its low 21 bits. One leak defeats the
  entire heap layout randomization for the process lifetime.

Per-request memory is capped by `memory_limit`. When an allocation inside the
parse window exceeds it, PHP aborts the request **immediately and
incompletely** — and the cleanup path for session state associated with the
request is where this bug lives.

## 3. Session upload progress

`session.upload_progress.enabled=On` makes PHP record multipart upload state
into the session **during the parse**: it decodes the session (creating the
in-memory `$_SESSION` structures), and updates progress entries keyed by the
`PHP_SESSION_UPLOAD_PROGRESS` form field. Your lab targets ship this On with
`session.use_strict_mode=0` — which is also why an attacker can choose the
session id freely.

Under an 8 M `memory_limit`, a ~12 MiB form **field** (a field, not a file
upload — files stream to disk, fields accumulate in memory) exhausts the
limit mid-parse, after the progress entry was created. The abort then leaves
session state referencing freed memory. That dangling reference is your
handle on the heap.

## 4. Why the config class matters

`memory_limit < post_max_size` (with room to spare) is what makes the abort
happen *inside* the parse instead of the request being cleanly rejected. Real
hosts ship exactly this: a tiny memory limit with a generous upload allowance.
Check A2 makes you read the effective values yourself — banners lie, `php -i`
in the container does not.

---

Continue to [02-the-bug.md](02-the-bug.md) for the failure mechanism, or
straight to [03-lab-guide.md](03-lab-guide.md) if you want to poke first and
read later.
