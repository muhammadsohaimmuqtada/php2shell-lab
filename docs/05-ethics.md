# 05 — Ethics, provenance, credits

## What this lab is

An educational range for a documented PHP-core vulnerability class
(CVE-2026-109618 / CVE-2026-109619, disclosed 2026-10-21, fixed in
8.2.35 / 8.3.36 / 8.4.27 / 8.5.12). Every target is a container you launch on
your machine, bound to `127.0.0.1`. The lab teaches heap exploitation on a
real, unpatched-in-the-wild bug class because abstractions (toy CTF binaries)
do not carry the operational lessons: worker lifetimes, SAPI differences,
config-class realities.

## What this lab is not

- Not a scanner, not an attack tool. It contains **no exploit code**; the
  chain is the learner's to build.
- Not a target list. The vulnerable builds here exist as public Docker Hub
  images and run only where you start them.
- Not permission. Nothing you learn transfers as authorization. Attacking
  systems you do not own or lack written authorization to test is a crime in
  most jurisdictions and always a bad look.

## Provenance

- The vulnerability and fix-window facts come from the public disclosure
  (2026-10-21) and the php-src fix commits.
- The 8.4-era chain and the `chunk + 0x690D8` payload constant were published
  by the original independent research; this lab credits and builds on it.
- The 8.3.35 payload constant, the ≤ 8.2 leak-severance
  analysis, the field-grade reliability data (25-worker keep-alive recipe),
  and the FPM fail-closed characterization originate from the author's
  engagement and are **deliberately withheld** from this lab (C3 and the
  hint ladder stop where those findings begin).
- Lab code: MIT. Docs: CC BY 4.0.

## Responsible follow-ups

If you derive something new (e.g., a fresh constant for another build, or a
working ≤ 8.2 leak channel): coordinate disclosure via the PHP security
process (security@php.net) before publishing. The EOL builds will never be
fixed — treat what you can do there as private research, not content.
