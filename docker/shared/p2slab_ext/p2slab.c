/*
 * p2slab — php2shell-lab randomizer extension.
 *
 * Per-boot instance randomization, derived from /lab/seed (32 random bytes,
 * 64 hex chars, mode 600, written by the lab entrypoint before Apache starts):
 *
 *   seed[0:16]  -> the boot canary (16 bytes) planted in the request heap
 *   seed[16]    -> layout shift: every request allocates 0x400*(k+1),
 *                  extra bytes at RINIT before anything else runs, so all
 *                  parse-time allocations — including the stage-3 payload
 *                  slot — move by an unknowable-per-boot delta. Published
 *                  payload constants are worthless on any given boot.
 *   seed[17:20] -> decoy pointer base (page-aligned, plausible 0x7f… form)
 *   seed[20:28] -> decoy pointer offsets
 *
 * RINIT plants a canary/decoy block (0x400) in every request:
 *   magic "P2SLABCB" + the boot canary + decoy pointer clusters that look
 *   statistically identical to real destructor-family pointers but never
 *   match live mappings. The block lives only inside the request heap, so
 *   it is visible in core dumps of a crashing worker — the forensics
 *   landmark — and invisible to between-request process inspection.
 *
 * If an aborted request skips RSHUTDOWN the block leaks — a few KB per OOM
 * abort, which is the lab's attempt budget made physical.
 *
 * NOTE: no layout shifting here on purpose. The multipart parse runs inside
 * sapi_activate, BEFORE zend_activate_modules, so no extension-side RINIT
 * allocation can move it. Per-boot randomization of the boss build comes
 * from the entrypoint randomizing memory_limit instead — see
 * docker/shared/entrypoint.sh.
 *
 * The seed is root-only. Nothing here prints the shift or canary anywhere.
 */

#ifdef HAVE_CONFIG_H
# include "config.h"
#endif

#include "php.h"
#include "ext/standard/info.h"
#include <stdio.h>
#include <string.h>

#define P2S_MAGIC   "P2SLABCB"
#define P2S_BLK     0x400
#define P2S_SEED    "/lab/seed"

typedef struct _p2s_globals {
    int ready;
    unsigned char canary[16];
    unsigned char decoy[16][8];
    void *decoy_block;
} p2s_globals;

static p2s_globals p2sg;

static int p2s_hexval(int c)
{
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return -1;
}

PHP_MINIT_FUNCTION(p2slab)
{
    FILE *f;
    char hex[130];
    unsigned char raw[32];
    size_t n, i;
    int hi, lo;

    memset(&p2sg, 0, sizeof(p2sg));

    f = fopen(P2S_SEED, "rb");
    if (!f) {
        return SUCCESS;  /* degrade: lab runs unrandomized (dev mode) */
    }
    n = fread(hex, 1, sizeof(hex) - 1, f);
    fclose(f);
    if (n < 64) {
        return SUCCESS;
    }
    for (i = 0; i < 32; i++) {
        hi = p2s_hexval((unsigned char)hex[2 * i]);
        lo = p2s_hexval((unsigned char)hex[2 * i + 1]);
        if (hi < 0 || lo < 0) {
            return SUCCESS;
        }
        raw[i] = (unsigned char)((hi << 4) | lo);
    }

    memcpy(p2sg.canary, raw, 16);

    {
        unsigned long long base, v;
        int j;
        base = 0x7f0000000000ULL
             | ((unsigned long long)raw[17] << 24)
             | ((unsigned long long)raw[18] << 16)
             | ((unsigned long long)raw[19] << 12);
        for (j = 0; j < 16; j++) {
            v = base + ((unsigned long long)raw[20 + (j & 7)] * 8 << 4);
            memset(p2sg.decoy[j], 0, 8);
            memcpy(p2sg.decoy[j], &v, 8);
        }
    }

    p2sg.ready = 1;
    return SUCCESS;
}

PHP_RINIT_FUNCTION(p2slab)
{
    if (p2sg.ready) {
        unsigned char *blk;
        int i;

        blk = (unsigned char *)emalloc(P2S_BLK);
        memset(blk, 0, P2S_BLK);
        memcpy(blk, P2S_MAGIC, 8);
        memcpy(blk + 8, p2sg.canary, 16);
        for (i = 0; i < 16; i++) {
            memcpy(blk + 0x40 + i * 8, p2sg.decoy[i], 8);
        }
        for (i = 0x100; i < P2S_BLK; i += 8) {
            memcpy(blk + i, "P2SNOISE", 8);
        }
        p2sg.decoy_block = blk;
    }
    return SUCCESS;
}

PHP_RSHUTDOWN_FUNCTION(p2slab)
{
    if (p2sg.decoy_block) {
        efree(p2sg.decoy_block);
        p2sg.decoy_block = NULL;
    }
    return SUCCESS;
}

PHP_MINFO_FUNCTION(p2slab)
{
    php_info_print_table_start();
    php_info_print_table_row(2, "p2slab support", "enabled");
    php_info_print_table_row(2, "randomization",
        p2sg.ready ? "active (per-boot seed)" : "inactive (no seed)");
    php_info_print_table_end();
}

zend_module_entry p2slab_module_entry = {
    STANDARD_MODULE_HEADER,
    "p2slab",
    NULL,                    /* no userspace functions */
    PHP_MINIT(p2slab),
    NULL,                    /* MSHUTDOWN */
    PHP_RINIT(p2slab),
    PHP_RSHUTDOWN(p2slab),
    PHP_MINFO(p2slab),
    "1.0.0",
    STANDARD_MODULE_PROPERTIES
};

#ifdef COMPILE_DL_P2SLAB
# ifdef ZTS
ZEND_TSRMLS_CACHE_DEFINE()
# endif
ZEND_GET_MODULE(p2slab)
#endif
