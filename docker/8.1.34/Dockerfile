# Intentionally vulnerable PHP 8.1.34 (mod_php + prefork). Lab use only.
# Build context is ./docker so the shared entrypoint is COPY-able:
#   docker build -f 8.1.34/Dockerfile -t p2slab/web-8.1.34 docker/
FROM php:8.1.34-apache
COPY shared/entrypoint.sh /usr/local/bin/lab-entrypoint.sh
RUN chmod +x /usr/local/bin/lab-entrypoint.sh
