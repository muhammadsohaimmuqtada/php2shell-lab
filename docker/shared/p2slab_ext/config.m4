PHP_ARG_ENABLE([p2slab],
  [whether to enable the p2slab randomizer],
  [AS_HELP_STRING([--enable-p2slab],
    [enable p2slab per-boot randomization])],
  [no])

if test "$PHP_P2SLAB" != "no"; then
  PHP_NEW_EXTENSION([p2slab], [p2slab.c], [$ext_shared])
fi
