# 02 — The bug: a dangling session entry across a parse abort

This document describes the mechanism at the level you need to build the
chain. It deliberately stops short of calibrated recipes: the spray shapes
are your work.

## The defect

On affected builds (everything before 8.2.35/8.3.36/8.4.27/8.5.12, and **all
of ≤ 8.1 forever**), the session-upload-progress lifecycle across an OOM
abort is inconsistent:

1. Request A begins the multipart parse. RINIT decoded the attacker-chosen
   session into memory; the upload-progress entry is created and referenced
   from the session structures.
2. The parse hits `memory_limit` on an attacker-sized field and aborts.
   Request memory is torn down — but parts of the session state associated
   with the progress entry survive in a **freed-and-dangling** configuration
   (CVE-2026-109618), and on some builds additional global state survives the
   abort into the next request (CVE-2026-109619).
3. Request B — same session id — decodes that damaged state back into a
   fresh request. The dangling reference now points into memory request B's
   own allocations can occupy.

## Turning it into a read primitive (B1/B2)

The freed slot is a predictable **size class**. Request B refills it with
attacker-shaped data: a `zend_string` whose header (the `len` field, 8 bytes
of which you control via field sizing) claims a much larger length than the
allocation. When PHP composes the response for request B, it treats that
forged header at face value and copies ~4096 bytes of **neighbouring heap**
into a `Set-Cookie` header.

Now you have an arbitrary-neighbourhood heap read, one spray at a time:

- B1: the neighbourhood contains zval/pointer values — cluster their high
  bits, mask, and you have the chunk base. Heap ASLR: gone.
- B2: change the refill shape so the neighbourhood contains a **function
  pointer** with a stable page offset (the destructor-family pointers). With
  A1's symbol offsets, bucket-and-subtract gives the module load base.
  Code ASLR (PIE): gone.

## Turning it into a write (C track)

The same dangling reference is also *written through* during session
shutdown. The chain's final move:

- plant a **fake HashTable** inside the chunk (your spray data), whose
  `pDestructor` points at `zif_system` (libphp base + A1 offset) and whose
  data pointer references a fake frame carrying your command string;
- arrange a short, deterministically-sized allocation to land **exactly on
  the dangling reference** so the session superglobal is redirected to your
  fake table;
- request shutdown destroys the "session array", walking your table and
  invoking `pDestructor` on one element: `system("your command")`, running
  as the worker's uid (www-data).

The address of the fake table inside the chunk is build-specific: the 8.4-era
layouts publish `chunk + 0x690D8`; 8.3.35 shifts it (see `forensics/`), and
deriving that constant is the boss fight. On ≤ 8.2 the read primitive is
severed at the source (`php_session_send_cookie` clears its send flag
unconditionally after the fix-era refactor *predates those branches*) —
you can still demonstrate the corruption (D1) and even crash the worker, but
no data comes back over HTTP. That is why the EOL corpus could never be
remotely exploited with a published chain, only with debugger-assisted
payload placement.

## What this teaches

- Parse-window failures are invisible to applications — and to most logging.
- Allocator determinism converts a one-shot UAF into a reliable primitive.
- ASLR is only as strong as the process's pointers' entropy: one 4096-byte
  read defeats it.
- Destructors are execution: any structure PHP walks at shutdown is a
  function-pointer slot if you can fake the table.

Next: [03-lab-guide.md](03-lab-guide.md).
