#ifndef ZEPHYR_PICKIT4_REPLACEMENT_PK4_RECOVERED_PROJECT_H_
#define ZEPHYR_PICKIT4_REPLACEMENT_PK4_RECOVERED_PROJECT_H_

#include <stddef.h>
#include <stdint.h>

#include "device_state.h"

enum pk4_recovered_slot_kind {
    PK4_RECOVERED_SLOT_BOOT = 0,
    PK4_RECOVERED_SLOT_PRIMARY_APP = 1,
    PK4_RECOVERED_SLOT_SECONDARY_APP = 2,
};

struct pk4_recovered_slot_descriptor {
    enum pk4_recovered_slot_kind kind;
    const char *name;
    const char *role;
    const char *identity;
    uint32_t base;
    uint32_t window_size;
    uint32_t initial_sp;
    uint32_t reset_vector;
};

struct pk4_recovered_project {
    const char *name;
    const char *target_family;
    struct pk4_recovered_slot_descriptor boot;
    struct pk4_recovered_slot_descriptor primary_app;
    struct pk4_recovered_slot_descriptor secondary_app;
};

void pk4_recovered_project_init(struct pk4_recovered_project *project, const struct device_state *state);
const struct pk4_recovered_slot_descriptor *pk4_recovered_project_get_slot(
    const struct pk4_recovered_project *project,
    enum pk4_recovered_slot_kind kind
);
int pk4_recovered_project_write_slot(
    struct device_state *state,
    enum pk4_recovered_slot_kind kind,
    uint32_t offset,
    const uint8_t *data,
    size_t size
);
int pk4_recovered_project_read_slot(
    const struct device_state *state,
    enum pk4_recovered_slot_kind kind,
    uint32_t offset,
    uint8_t *data,
    size_t size
);

#endif