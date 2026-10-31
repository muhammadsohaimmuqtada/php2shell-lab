# Intentionally vulnerable PHP 8.5.11 (mod_php + prefork). Lab use only.
# Build context is ./docker so the shared entrypoint is COPY-able:
#   docker build -f 8.5.11/Dockerfile -t p2slab/web-8.5.11 docker/
FROM php:8.5.11-apache
COPY shared/entrypoint.sh /usr/local/bin/lab-entrypoint.sh
RUN chmod +x /usr/local/bin/lab-entrypoint.sh
