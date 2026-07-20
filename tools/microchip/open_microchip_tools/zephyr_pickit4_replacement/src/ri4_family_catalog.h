#ifndef ZEPHYR_PICKIT4_REPLACEMENT_RI4_FAMILY_CATALOG_H_
#define ZEPHYR_PICKIT4_REPLACEMENT_RI4_FAMILY_CATALOG_H_

#include <stdbool.h>
#include <stddef.h>

struct ri4_family_catalog_entry {
    const char *family;
    const char *behavior;
    bool supports_programming;
    bool supports_debugging;
    bool supports_set_pc;
    const char * const *scripts;
    size_t script_count;
};

#if __has_include("ri4_family_catalog_data.h")
#include "ri4_family_catalog_data.h"
#else
static const struct ri4_family_catalog_entry ri4_family_catalog[] = {
};
static const size_t ri4_family_catalog_count = 0U;
#endif

#endif