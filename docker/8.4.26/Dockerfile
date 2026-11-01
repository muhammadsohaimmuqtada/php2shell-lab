# Intentionally vulnerable PHP 8.4.26 (mod_php + prefork) + p2slab randomizer.
# Build context is ./docker:
#   docker build -f 8.4.26/Dockerfile -t p2slab/web-8.4.26 docker/
FROM php:8.4.26-apache

# p2slab: per-boot layout shift + canary/decoy planter (see shared/p2slab_ext/)
COPY shared/p2slab_ext /usr/src/p2slab_ext
RUN cd /usr/src/p2slab_ext     && phpize     && ./configure --enable-p2slab     && make -j"$(nproc)"     && make install     && docker-php-ext-enable p2slab     && rm -rf /usr/src/p2slab_ext

COPY shared/entrypoint.sh /usr/local/bin/lab-entrypoint.sh
RUN chmod +x /usr/local/bin/lab-entrypoint.sh

CMD ["apache2-foreground"]
