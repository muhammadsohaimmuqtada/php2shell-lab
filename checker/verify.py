#!/usr/bin/env python3
"""Live-target verification for the php2shell lab.

Every stage submission is checked against the *running* container: leaked
pointers must appear in a worker's /proc/<pid>/maps, the zif_system offset
must match the container's actual libphp.so, and the flag can only come from
code that executed inside the container.

Docker is required (the checker shells out to `docker exec` / `docker cp`).
"""
from __future__ import annotations

import re
import struct
import subprocess
import sys
import tempfile
import os

CONTAINERS = {
    "8.1.34": "p2slab-8134",
    "8.3.35": "p2slab-8335",
    "8.4.25": "p2slab-8425",
    "8.4.26": "p2slab-8426",
    "8.5.10": "p2slab-8510",
    "8.5.11": "p2slab-8511",
}

SPT_SYMTAB = 2
SHT_DYNSYM = 11
PT_LOAD = 1


class VerifyError(Exception):
    pass


def sh(args: list[str], check: bool = True) -> str:
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=60)
    except FileNotFoundError:
        raise VerifyError("docker not found — is Docker installed and in PATH?")
    if check and r.returncode != 0:
        raise VerifyError(f"command failed: {' '.join(args)}\n{r.stderr.strip()[:200]}")
    return r.stdout


def container_up(version: str) -> str:
    name = CONTAINERS.get(version)
    if not name:
        raise VerifyError(f"unknown version {version!r}")
    out = sh(["docker", "ps", "--format", "{{.Names}}"], check=False)
    if name not in out.split():
        raise VerifyError(
            f"container {name} is not running — start it: ./labctl start {version}"
        )
    return name


def worker_pids(name: str) -> list[int]:
    out = sh(["docker", "exec", name, "ps", "-eo", "pid,comm,args"], check=False)
    pids = []
    for line in out.splitlines()[1:]:
        parts = line.split(None, 2)
        if len(parts) < 3:
            continue
        if "apache2" in parts[1] or "apache2" in parts[2]:
            pids.append(int(parts[0]))
    if not pids:
        raise VerifyError("no apache2 processes found in container — is it up?")
    return pids


def parse_maps(text: str) -> list[dict]:
    maps = []
    for line in text.splitlines():
        m = re.match(
            r"([0-9a-f]+)-([0-9a-f]+) (\S+) (\S+) (\S+) (\S+)\s*(.*)", line
        )
        if not m:
            continue
        start, end = int(m.group(1), 16), int(m.group(2), 16)
        maps.append({
            "start": start, "end": end, "perms": m.group(3),
            "size": end - start, "path": m.group(7).strip(),
        })
    return maps


def all_worker_maps(name: str) -> list[list[dict]]:
    out = []
    for pid in worker_pids(name):
        text = sh(["docker", "exec", name, "cat", f"/proc/{pid}/maps"], check=False)
        if text:
            out.append(parse_maps(text))
    return out


def libphp_base(maps: list[dict]) -> int | None:
    bases = [m["start"] for m in maps
             if "libphp" in m["path"] and m["path"].endswith(".so")]
    return min(bases) if bases else None


def check_chunk(version: str, addr: int) -> tuple[bool, str]:
    """A chunk base must be 2 MiB-aligned and sit inside a large anonymous
    rw mapping of a live worker (Zend MM chunks are mmap'd 2 MiB arenas)."""
    if addr & 0x1FFFFF:
        return False, "address is not 2 MiB-aligned (chunk bases always are)"
    name = container_up(version)
    for maps in all_worker_maps(name):
        for m in maps:
            if (not m["path"] and "w" in m["perms"]
                    and m["start"] <= addr < m["end"] and m["size"] >= 1 << 20):
                if m["start"] == addr:
                    return True, "exact 2 MiB anonymous arena start — textbook"
                return True, "inside a large anonymous rw arena of a live worker"
    return False, ("no live worker has an anonymous rw arena covering that "
                   "address — the leak is not real (or the worker died; retry)")


def check_libphp(version: str, addr: int) -> tuple[bool, str]:
    if addr & 0xFFF:
        return False, "load bases are always page-aligned"
    name = container_up(version)
    for maps in all_worker_maps(name):
        base = libphp_base(maps)
        if base is not None and base == addr:
            return True, "matches the live libphp.so load base — PIE defeated"
    return False, ("no live worker maps libphp.so at that address "
                   "(wrong leak, or the worker rotated — retry)")


def check_zif(version: str, off: int) -> tuple[bool, str]:
    real, _ = extract_symbols(version)
    if real is None:
        return False, "could not read symbols from the container"
    if real == off:
        return True, f"correct: zif_system is at libphp+{hex(off)}"
    return False, f"not the offset in this container's libphp.so (yours: {hex(off)})"


def check_flag(version: str, value: str) -> tuple[bool, str]:
    name = container_up(version)
    real = sh(["docker", "exec", name, "cat", "/flag"]).strip()
    got = value.strip().lower().replace("0x", "")
    if not re.fullmatch(r"[0-9a-f]{32}", got):
        return False, "flag format is 32 hex chars (contents of /flag)"
    if got == real:
        return True, "flag matches — code execution confirmed"
    return False, "wrong flag — that is not what /flag holds right now"


def check_config(version: str, value: str) -> tuple[bool, str]:
    name = container_up(version)
    ini = sh(["docker", "exec", name, "php", "-i"], check=False)
    mem = re.search(r"(?m)^memory_limit\s*=>\s*(\S+)", ini)
    post = re.search(r"(?m)^post_max_size\s*=>\s*(\S+)", ini)
    got = [v.strip().lower() for v in value.replace(";", ",").split(",")]
    want = [mem.group(1).lower() if mem else "?", post.group(1).lower() if post else "?"]
    if got == want:
        return True, f"correct: memory_limit={want[0]}, post_max_size={want[1]}"
    return False, f"not what this SAPI reports (hint: it reports two values, comma-separated)"


def check_oom_n(value: str) -> tuple[bool, str]:
    try:
        n = int(value.strip(), 0)
    except ValueError:
        return False, "submit the integer N from 'tried to allocate N bytes'"
    # The abort happens while the parse buffers a 12 MiB form field against
    # an 8M limit, so a genuine N is large — sub-1MiB values never occur.
    if 1 << 20 <= n <= (1 << 24):
        return True, (f"plausible abort size ({n} bytes) accepted. This one is "
                      "honor-based: you know whether you really saw the fatal.")
    return False, "N is outside the plausible range for this config class"


# ---------------------------------------------------------------- ELF symbols

def extract_symbols(version: str) -> tuple[int | None, int | None]:
    """(zif_system, zval_ptr_dtor) offsets in the container's libphp.so."""
    name = container_up(version)
    listing = sh(["docker", "exec", name,
                  "ls", "/usr/lib/apache2/modules/"], check=False)
    lib = None
    for line in listing.split():
        if line.startswith("libphp") and line.endswith(".so"):
            lib = f"/usr/lib/apache2/modules/{line}"
    if not lib:
        return None, None
    fd, path = tempfile.mkstemp(prefix="libphp-", suffix=".so")
    os.close(fd)
    try:
        sh(["docker", "cp", f"{name}:{lib}", path])
        return parse_elf_symbols(path)
    finally:
        os.unlink(path)


def parse_elf_symbols(path: str) -> tuple[int | None, int | None]:
    data = open(path, "rb").read()
    if data[:4] != b"\x7fELF" or data[4] != 2 or data[5] != 1:
        raise VerifyError("libphp.so is not ELF64 LE")
    e_shoff, = struct.unpack_from("<Q", data, 0x28)
    e_shentsize, e_shnum = struct.unpack_from("<HH", data, 0x3A)
    e_shstrndx, = struct.unpack_from("<H", data, 0x3E)
    sections = []
    for i in range(e_shnum):
        off = e_shoff + i * e_shentsize
        sh_name, sh_type, _flags, _addr, sh_offset, sh_size, sh_link, _info, _align, sh_entsize = \
            struct.unpack_from("<IIQQQQIIQQ", data, off)
        sections.append((sh_name, sh_type, sh_offset, sh_size, sh_link, sh_entsize))
    if e_shstrndx >= len(sections):
        return None, None
    stroff = sections[e_shstrndx][2]
    def sname(no):
        end = data.find(b"\x00", stroff + no)
        return data[stroff + no:end].decode("ascii", "replace")
    wanted = {"zif_system": None, "zval_ptr_dtor": None, "_zval_ptr_dtor": None}
    for sh_name, sh_type, sh_offset, sh_size, sh_link, sh_entsize in sections:
        if sh_type not in (SPT_SYMTAB, SHT_DYNSYM) or sh_link >= len(sections):
            continue
        strtab = sections[sh_link]
        entsize = sh_entsize or 24
        for i in range(sh_size // entsize):
            off = sh_offset + i * entsize
            st_name, = struct.unpack_from("<I", data, off)
            if not st_name:
                continue
            nm_off = strtab[2] + st_name
            end = data.find(b"\x00", nm_off)
            nm = data[nm_off:end].decode("ascii", "replace")
            if nm in wanted and wanted[nm] is None:
                st_value, = struct.unpack_from("<Q", data, off + 8)
                wanted[nm] = st_value
    # libphp .so may export the dtor only as the versioned/unprefixed alias
    dtor = wanted["zval_ptr_dtor"] or wanted["_zval_ptr_dtor"]
    return wanted["zif_system"], dtor
