# Heap forensics — how you earn the boss constant

The 8.3.35 boss fight exists because the stage-3 payload address inside the
2 MiB Zend chunk is **not published anywhere** for that build. The 8.4-era
layout (`chunk + 0x690D8`) is documented public research — but 8.3 objects
have no `extra_flags` field, every allocation after the object shifts, and
the payload therefore lands at a different offset. Nobody hands it to you.
You measure it.

## The idea

Your stage-3 payload is a fake structure you sprayed into the chunk. If the
address you gave the chain is wrong, the worker dies *somehow* — and a
segfaulting worker leaves evidence. You control the payload bytes, so you
control a **signature**: a marker string inside the sprayed structure that
cannot appear in normal heap traffic. Find the signature in the dead worker's
heap, compute its distance from the chunk base, and you have your constant.

## Recipe

1. **Get a core.** Either:
   - set `kernel.core_pattern=/tmp/core.%p` on the host (lab machines only),
     let the container's worker crash, and `docker cp` the core out of the
     container (Apache dumps into `/etc/apache2` per its `CoreDumpDirectory`), or
   - run the container with `--cap-add=SYS_PTRACE`, `gdb -p <worker pid>` on
     the host side of the container, and `gcore`.
2. **Locate the chunk.** In the core, the Zend chunk is a 2 MiB region whose
   base you already know from your B1 leak (same worker, same boot — if you
   leaked before crashing, the address still holds; workers don't re-ASLR
   within a process lifetime).
3. **Scan for the signature.** `forensics/core-scan.py` walks the region and
   reports every offset where your marker appears, relative to the chunk base.
4. **Recompute.** The constant you need is the offset of the *structure base*,
   not of the marker — account for where in your fake structure the marker
   sits (you laid it out; you know the delta).
5. **Verify the shape.** The correct constant makes stage 3 land the carrier
   exactly on the dangling reference: `chunk + <constant>` in your stage-3
   call, proof file appears, `/flag` is readable.

`core-scan.py` usage:

```bash
python3 forensics/core-scan.py core.1234 --chunk 0x7f3c20000000 --sig "P2SBOSS1"
```

It prints each hit as `chunk + 0x…`. One of those hits — shifted by your
known marker-to-structure delta — is the boss constant. When your stage 3
succeeds and `./labctl submit 8335 C3 <flag>` accepts, you have reproduced,
from scratch, a result that took the original engagement a gdb session and
three crash cycles to measure.

## Why this is the good part

Everything up to here (B1/B2/C1) taught you a documented chain. This step is
*research*: the skill of turning a controlled crash into a calibrated
exploit. That is the difference between running someone's exploit and
writing one.
