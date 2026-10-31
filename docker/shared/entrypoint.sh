#!/bin/sh
# Lab entrypoint: mint the per-boot seed + flag, then hand off to the SAPI.
# /lab/seed (600 root) drives the p2slab extension's per-boot randomization.
# /flag is 640 root:www-data — only code running as www-data (i.e. real
# code execution inside the request lifecycle) can read it.
set -e

mkdir -p /lab /out

SEED="$(head -c 32 /dev/urandom | od -An -tx1 | tr -d ' \n')"
printf '%s' "$SEED" > /lab/seed
chmod 600 /lab/seed
chown root:root /lab/seed

FLAG="$(head -c 16 /dev/urandom | od -An -tx1 | tr -d ' \n')"
printf '%s' "$FLAG" > /flag
chown root:www-data /flag
chmod 640 /flag

# Writable staging dir mounted from the host: proof files and the 8-byte
# `sh</out/c` script pattern land here (see hints + lab guide).
chown www-data:www-data /out 2>/dev/null || true
chmod 777 /out 2>/dev/null || true

# Lab ini: written per boot from the mounted template. With P2S_RAND_MEM=1
# (the boss build) memory_limit is seed-derived within the same config
# class — the parse-time abort geometry, the freed-slot layout and thus the
# stage-3 payload constant differ on every boot. No heap patching involved:
# this is the exact config-class variance the real world runs with.
if [ -f /opt/lab/php.ini.template ]; then
    MEM=8M
    if [ "${P2S_RAND_MEM:-0}" = "1" ]; then
        B0=$(( 0x$(printf '%s' "$SEED" | cut -c1-2) % 7 ))
        MEM="$((6 + B0))M"
    fi
    sed "s/^memory_limit.*/memory_limit = ${MEM}/" /opt/lab/php.ini.template \
        > /usr/local/etc/php/conf.d/zz-lab.ini
    chmod 644 /usr/local/etc/php/conf.d/zz-lab.ini
    echo "[lab] memory_limit=${MEM}$([ "${P2S_RAND_MEM:-0}" = "1" ] && echo ' (randomized this boot)')"
fi

echo "[lab] seed written (64 hex chars), flag minted (${#FLAG} hex chars)."
exec "$@"
