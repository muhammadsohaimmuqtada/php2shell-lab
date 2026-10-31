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

echo "[lab] seed written (64 hex chars), flag minted (${#FLAG} hex chars)."
exec "$@"
