# Intentionally vulnerable PHP 8.5.10 (mod_php + prefork) + p2slab randomizer.
# Build context is ./docker:
#   docker build -f 8.5.10/Dockerfile -t p2slab/web-8.5.10 docker/
FROM php:8.5.10-apache

# p2slab: per-boot layout shift + canary/decoy planter (see shared/p2slab_ext/)
COPY shared/p2slab_ext /usr/src/p2slab_ext
RUN cd /usr/src/p2slab_ext     && phpize     && ./configure --enable-p2slab     && make -j"$(nproc)"     && make install     && docker-php-ext-enable p2slab     && rm -rf /usr/src/p2slab_ext

COPY shared/entrypoint.sh /usr/local/bin/lab-entrypoint.sh
RUN chmod +x /usr/local/bin/lab-entrypoint.sh
