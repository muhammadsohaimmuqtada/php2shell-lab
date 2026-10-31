"""Spoiler-gated hints, read via ./labctl hint <ID> <level>.

Level 1 points at the concept, level 2 narrows the technique, level 3 gives
the concrete mechanism — but never a working recipe. Calibrated spray shapes
and the boss-build payload address are not in this file, anywhere.
"""

HINTS = {
    "A1": [
        "The offset is a property of the binary, not of the running process. "
        "Which ELF section maps symbol names to addresses?",
        "docker cp the libphp.so out of the container and parse its symbol "
        "table (SHT_SYMTAB / SHT_DYNSYM). `recon/symbols.py` does this for you "
        "— read it and make sure you understand every line.",
        "zif_system = st_value of the 'zif_system' symbol minus the lowest "
        "PT_LOAD p_vaddr (the module's link-time base). The result is "
        "PIE-independent: it is an offset, not an address.",
    ],
    "A2": [
        "php -i in the container shows the CLI SAPI — the web SAPI can differ. "
        "Check what the lab actually mounts where.",
        "srv/php.ini is mounted into conf.d, which both SAPIs read. So CLI "
        "and web agree here. Which two directives define this config class?",
        "memory_limit is the small one, post_max_size the large one. Their "
        "ratio is what makes the parse abort instead of rejecting the body.",
    ],
    "B1": [
        "You need PHP to echo heap bytes it should not. Read docs/02: the "
        "abort leaves a dangling session-upload-progress entry; the next "
        "request can refill that slot.",
        "Craft a request that (1) aborts mid-parse with a upload-progress "
        "entry already created, then (2) a follow-up request whose field "
        "sizes refill the freed slot with a zend_string whose header you "
        "control. The session id you receive is then a forged-length string.",
        "The echoed bytes come from a Set-Cookie of ~4096 bytes. Parse the "
        "8-byte aligned values in it and look for pointer clustering: many "
        "values sharing a high-33-bits prefix. That prefix region is the "
        "2 MiB chunk — its base is (value & ~0x1FFFFF).",
    ],
    "B2": [
        "Same forged-length primitive, different refill shape: you need the "
        "neighbouring heap to contain a pointer INTO the PHP binary itself.",
        "One of the sprayed fields should be an array whose element table "
        "lands in the recycled slot; the table's pDestructor-style slots "
        "hold function pointers with page-aligned low 12 bits. Beware: the "
        "neighbourhood is full of plausible-looking fakes — plausible is "
        "not correct.",
        "Dump the leak, bucket all 8-byte aligned values by (v & ~0xFFF) "
        "popularity, and test which bucket minus each candidate offset "
        "(zval_ptr_dtor is the classic) yields a page-aligned libphp base. "
        "Expect decoys: fake clusters that cluster beautifully and verify "
        "wrong. Only live /proc/<pid>/maps tells the truth. Submit "
        "`libphp_base,canary`.", 
    ],
    "B3": [
        "If your leak works on one build it should work on its siblings — "
        "the mechanism did not change between them.",
        "Watch the freed-slot sizes: they are set by the aborting request, "
        "which is identical across these builds.",
        "Only the pointer-cluster thresholds should need retuning. If a "
        "build refuses, sweep the refill count N in small steps.",
    ],
    "C1": [
        "You have chunk and libphp bases. Stage 3 = get a controlled value "
        "written where PS(http_session_vars) points, then let PHP's own "
        "shutdown walk it.",
        "The write lands via a short allocated string that must sit exactly "
        "on the dangling reference. Which allocation size is deterministic "
        "across requests? A 15-byte string in the right slot.",
        "The fake HashTable's pDestructor is your function pointer: "
        "libphp_base + zif_offset. Its data pointer must reference a fake "
        "stack frame carrying your command string. Keep the command ≤ 14 "
        "bytes — 'sh</out/c' is 8 if you can write a script file first.",
    ],
    "C2": [
        "The family builds share the same internals module layout.",
        "The payload address inside the chunk for the 8.4-era layout is a "
        "published public constant: chunk + 0x690D8 (extra_flags field "
        "shifts 8.4+ objects vs 8.3).",
        "Everything else is your working 8.4.25 chain. Mind worker state: "
        "each attempt should start from a worker you have calibrated.",
    ],
    "C3": [
        "8.3.35 predates the extra_flags field, so 8.4-era offsets do not "
        "apply. Worse: every boot shifts the heap (the lab's p2slab "
        "extension moves early request allocations by a seed-derived "
        "delta), so the payload address changes on every restart. Nobody "
        "can hand you this constant — not upstream, not this repo, not a "
        "previous boot of your own.",
        "Get a crash under control first: make stage 3 fire with a wrong "
        "address, let the worker segfault, capture the core (core_pattern, "
        "or run the container with a ptrace-attached gdb). See forensics/ "
        "— the extension's shift block ('A'-run) and canary block are "
        "findable landmarks by design.",
        "In the core, find the spray: search the 2 MiB chunk region for "
        "your payload signature (a marker string you placed in a known "
        "part of the fake structure). For each hit, subtract the marker's "
        "offset within your fake structure from its offset in the chunk — "
        "that is this boot's constant. Re-measure after every restart.",
    ],
    "D1": [
        "The research yard exists because on ≤ 8.2 the leak channel is "
        "severed — the corruption still fires, you just get nothing back "
        "over HTTP.",
        "POST a plain form FIELD (not a file upload — files stream to disk) "
        "large enough to exhaust memory_limit mid-parse, with the "
        "upload-progress session cookie set.",
        "display_errors=On is your friend: the fatal names the allocation "
        "that died — 'Allowed memory size of 8388608 bytes exhausted (tried "
        "to allocate N bytes) in Unknown on line 0'. Submit N.",
    ],
}
