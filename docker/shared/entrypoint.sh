#!/bin/sh
# Lab entrypoint: mint the per-boot flag, then hand off to the SAPI.
# /flag is 640 root:www-data — only code running as www-data (i.e. real
# code execution inside the request lifecycle) can read it.
set -e

FLAG="$(head -c 16 /dev/urandom | od -An -tx1 | tr -d ' \n')"
printf '%s' "$FLAG" > /flag
chown root:www-data /flag
chmod 640 /flag

# Writable staging dir mounted from the host: proof files and the 8-byte
# `sh</out/c` script pattern land here (see hints + lab guide).
mkdir -p /out && chown www-data:www-data /out && chmod 777 /out

echo "[lab] flag minted (${#FLAG} hex chars)."
exec "$@"
