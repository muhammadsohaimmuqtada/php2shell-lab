#!/usr/bin/env python3
"""recon/symbols.py — extract zif_system / zval_ptr_dtor offsets from a lab
container's libphp.so (educational reference implementation).

    python3 recon/symbols.py 8.4.25
"""
from __future__ import annotations

import os
import struct
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "checker"))
from verify import CONTAINERS  # noqa: E402

SHT_SYMTAB, SHT_DYNSYM = 2, 11


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    version = sys.argv[1]
    name = CONTAINERS[version]

    listing = subprocess.run(["docker", "exec", name, "ls", "/usr/lib/apache2/modules/"],
                             capture_output=True, text=True).stdout.split()
    lib = next((f"/usr/lib/apache2/modules/{f}" for f in listing
                if f.startswith("libphp") and f.endswith(".so")), None)
    if not lib:
        print("no libphp*.so found — is this a mod_php build?")
        return 1

    fd, path = tempfile.mkstemp(prefix="libphp-", suffix=".so")
    os.close(fd)
    subprocess.run(["docker", "cp", f"{name}:{lib}", path], check=True)
    data = open(path, "rb").read()
    os.unlink(path)

    e_shoff, = struct.unpack_from("<Q", data, 0x28)
    e_shentsize, e_shnum = struct.unpack_from("<HH", data, 0x3A)
    e_shstrndx, = struct.unpack_from("<H", data, 0x3E)
    sections = []
    for i in range(e_shnum):
        off = e_shoff + i * e_shentsize
        vals = struct.unpack_from("<IIQQQQIIQQ", data, off)
        sections.append(dict(name=vals[0], type=vals[1], offset=vals[4],
                             size=vals[5], link=vals[6], entsize=vals[9]))
    stroff = sections[e_shstrndx]["offset"]
    loads = []
    # PT_LOAD walk for the link-time base (st_value is a virtual address)
    e_phoff, = struct.unpack_from("<Q", data, 0x20)
    e_phentsize, e_phnum = struct.unpack_from("<HH", data, 0x36)
    for i in range(e_phnum):
        off = e_phoff + i * e_phentsize
        p_type, = struct.unpack_from("<I", data, off)
        p_vaddr, = struct.unpack_from("<Q", data, off + 16)
        if p_type == 1:
            loads.append(p_vaddr)
    bias = min(loads) if loads else 0

    found = {}
    for sec in sections:
        if sec["type"] not in (SHT_SYMTAB, SHT_DYNSYM) or sec["link"] >= len(sections):
            continue
        strtab = sections[sec["link"]]["offset"]
        entsize = sec["entsize"] or 24
        for i in range(sec["size"] // entsize):
            off = sec["offset"] + i * entsize
            st_name, = struct.unpack_from("<I", data, off)
            if not st_name:
                continue
            no = strtab + st_name
            end = data.find(b"\x00", no)
            nm = data[no:end].decode("ascii", "replace")
            if nm in ("zif_system", "zval_ptr_dtor", "_zval_ptr_dtor") and nm not in found:
                st_value, = struct.unpack_from("<Q", data, off + 8)
                found[nm] = st_value

    print(f"[+] {name} :: {lib}")
    print(f"    link-time base (min PT_LOAD vaddr): {hex(bias)}")
    for k in ("zif_system", "zval_ptr_dtor", "_zval_ptr_dtor"):
        if k in found:
            print(f"    {k:16} {hex(found[k])}  ->  module offset {hex(found[k] - bias)}")
    print("\n    These are OFFSETS: valid at any load address (PIE). Your B2")
    print("    leak gives you the runtime load base; add offsets to it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
