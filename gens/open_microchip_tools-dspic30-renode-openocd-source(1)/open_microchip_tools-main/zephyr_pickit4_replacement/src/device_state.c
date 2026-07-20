#include "device_state.h"

#include <errno.h>
#include <stdio.h>
#include <string.h>

#include "pk4_observed_firmware_profile.h"

static const struct device_state_profile g_pk4_profile = {
    .name = "PK4_OBSERVED_DUAL_APP_LAYOUT",
    .family = "ARM_MPU",
    .secondary_role = "CMSIS-DAP control/update slot",
    .secondary_identity = PK4_OBS_APP2_IDENTITY,
    .boot_base = PK4_OBS_BOOT_BASE,
    .app_base = PK4_OBS_APP_BASE,
    .app2_base = PK4_OBS_APP2_BASE,
    .initial_sp = PK4_OBS_APP_INITIAL_SP,
    .reset_vector = PK4_OBS_APP_RESET_VECTOR,
    .app2_initial_sp = PK4_OBS_APP2_INITIAL_SP,
    .app2_reset_vector = PK4_OBS_APP2_RESET_VECTOR,
    .boot_window_size = DEVICE_STATE_BOOT_WINDOW_SIZE,
    .app_window_size = DEVICE_STATE_APP_WINDOW_SIZE,
    .app2_window_size = DEVICE_STATE_APP2_WINDOW_SIZE,
};

struct flash_region_view {
    uint8_t *data;
    uint32_t base;
    uint32_t size;
    const char *name;
};

static const char *region_role(const struct device_state *state, const char *region_name)
{
    (void)state;

    if (strcmp(region_name, "boot") == 0) {
        return "boot strap slot";
    }
    if (strcmp(region_name, "app") == 0) {
        return "RI4 host-facing app slot";
    }
    if (strcmp(region_name, "app2") == 0) {
        return g_pk4_profile.secondary_role;
    }
    return "unknown";
}

static const char *slot_name_for_pc(const struct device_state *state)
{
    if (state->pc >= state->profile->boot_base && state->pc < (state->profile->boot_base + state->profile->boot_window_size)) {
        return "boot";
    }
    if (state->pc >= state->profile->app_base && state->pc < (state->profile->app_base + state->profile->app_window_size)) {
        return "app";
    }
    if (state->pc >= state->profile->app2_base && state->pc < (state->profile->app2_base + state->profile->app2_window_size)) {
        return "app2";
    }
    return "external";
}

static void set_last_program_region(struct device_state *state, const char *region_name)
{
    snprintf(state->last_program_region, sizeof(state->last_program_region), "%s", region_name);
    snprintf(state->last_program_role, sizeof(state->last_program_role), "%s", region_role(state, region_name));
}

static int translate_flash_address(
    const struct device_state *state,
    uint32_t address,
    size_t size,
    struct flash_region_view *region,
    size_t *offset
)
{
    uint32_t normalized;
    uint32_t region_size;
    uint32_t region_base;

    if (address >= state->profile->boot_base && address < (state->profile->boot_base + state->profile->boot_window_size)) {
        region->data = (uint8_t *)state->boot_flash_window;
        region->base = state->profile->boot_base;
        region->size = state->profile->boot_window_size;
        region->name = "boot";
    } else if (address >= state->profile->app_base && address < (state->profile->app_base + state->profile->app_window_size)) {
        region->data = (uint8_t *)state->app_flash_window;
        region->base = state->profile->app_base;
        region->size = state->profile->app_window_size;
        region->name = "app";
    } else if (address >= state->profile->app2_base && address < (state->profile->app2_base + state->profile->app2_window_size)) {
        region->data = (uint8_t *)state->app2_flash_window;
        region->base = state->profile->app2_base;
        region->size = state->profile->app2_window_size;
        region->name = "app2";
    } else if (address < state->profile->app_window_size) {
        region->data = (uint8_t *)state->app_flash_window;
        region->base = state->profile->app_base;
        region->size = state->profile->app_window_size;
        region->name = "app";
    } else {
        return -ERANGE;
    }

    region_base = region->base;
    region_size = region->size;

    if (address < region_size) {
        normalized = address;
    } else if (address >= region_base) {
        normalized = address - region_base;
    } else {
        return -ERANGE;
    }

    if ((size > 0U) && (normalized > (region_size - size))) {
        return -ERANGE;
    }

    *offset = (size_t)normalized;
    return 0;
}

void device_state_init(struct device_state *state)
{
    memset(state, 0, sizeof(*state));
    state->profile = &g_pk4_profile;
    set_last_program_region(state, "none");
    device_state_erase_flash(state);
    device_state_reset(state);
}

void device_state_reset(struct device_state *state)
{
    state->debug_mode = false;
    state->halted = false;
    state->pc = state->profile->reset_vector;
}

void device_state_halt(struct device_state *state)
{
    state->debug_mode = true;
    state->halted = true;
}

void device_state_run(struct device_state *state)
{
    state->debug_mode = true;
    state->halted = false;
}

void device_state_step(struct device_state *state)
{
    state->debug_mode = true;
    state->halted = true;
    state->pc += 2U;
}

void device_state_set_pc(struct device_state *state, uint32_t pc)
{
    state->pc = pc;
}

uint32_t device_state_get_pc(const struct device_state *state)
{
    return state->pc;
}

void device_state_erase_flash(struct device_state *state)
{
    memset(state->boot_flash_window, 0xFF, sizeof(state->boot_flash_window));
    memset(state->app_flash_window, 0xFF, sizeof(state->app_flash_window));
    memset(state->app2_flash_window, 0xFF, sizeof(state->app2_flash_window));
    set_last_program_region(state, "chip-erase");
}

int device_state_write_flash(struct device_state *state, uint32_t address, const uint8_t *data, size_t size)
{
    struct flash_region_view region;
    size_t offset;

    if (translate_flash_address(state, address, size, &region, &offset) != 0) {
        return -ERANGE;
    }

    memcpy(&region.data[offset], data, size);
    set_last_program_region(state, region.name);
    return 0;
}

int device_state_read_flash(const struct device_state *state, uint32_t address, uint8_t *data, size_t size)
{
    struct flash_region_view region;
    size_t offset;

    if (translate_flash_address(state, address, size, &region, &offset) != 0) {
        return -ERANGE;
    }

    memcpy(data, &region.data[offset], size);
    ((struct device_state *)state)->last_program_region[0] = '\0';
    ((struct device_state *)state)->last_program_role[0] = '\0';
    set_last_program_region((struct device_state *)state, region.name);
    return 0;
}

int device_state_write_primary_slot(struct device_state *state, uint32_t offset, const uint8_t *data, size_t size)
{
    return device_state_write_flash(state, state->profile->app_base + offset, data, size);
}

int device_state_read_primary_slot(const struct device_state *state, uint32_t offset, uint8_t *data, size_t size)
{
    return device_state_read_flash(state, state->profile->app_base + offset, data, size);
}

int device_state_write_secondary_slot(struct device_state *state, uint32_t offset, const uint8_t *data, size_t size)
{
    return device_state_write_flash(state, state->profile->app2_base + offset, data, size);
}

int device_state_read_secondary_slot(const struct device_state *state, uint32_t offset, uint8_t *data, size_t size)
{
    return device_state_read_flash(state, state->profile->app2_base + offset, data, size);
}

const struct device_state_profile *device_state_get_profile(const struct device_state *state)
{
    return state->profile;
}

const char *device_state_get_family(const struct device_state *state)
{
    return state->profile->family;
}

const char *device_state_get_profile_name(const struct device_state *state)
{
    return state->profile->name;
}

uint32_t device_state_get_flash_window_base(const struct device_state *state)
{
    return state->profile->boot_base;
}

uint32_t device_state_get_boot_window_size(const struct device_state *state)
{
    return state->profile->boot_window_size;
}

uint32_t device_state_get_app_window_base(const struct device_state *state)
{
    return state->profile->app_base;
}

uint32_t device_state_get_app_window_size(const struct device_state *state)
{
    return state->profile->app_window_size;
}

uint32_t device_state_get_app2_window_base(const struct device_state *state)
{
    return state->profile->app2_base;
}

uint32_t device_state_get_app2_window_size(const struct device_state *state)
{
    return state->profile->app2_window_size;
}

const char *device_state_get_status_value(struct device_state *state, const char *key)
{
    if (strcmp(key, "Family") == 0) {
        return state->profile->family;
    }
    if (strcmp(key, "Probe Profile") == 0) {
        return state->profile->name;
    }
    if (strcmp(key, "Boot Base") == 0) {
        snprintf(state->status_value, sizeof(state->status_value), "0x%08X", state->profile->boot_base);
        return state->status_value;
    }
    if (strcmp(key, "App Base") == 0) {
        snprintf(state->status_value, sizeof(state->status_value), "0x%08X", state->profile->app_base);
        return state->status_value;
    }
    if (strcmp(key, "App2 Base") == 0) {
        snprintf(state->status_value, sizeof(state->status_value), "0x%08X", state->profile->app2_base);
        return state->status_value;
    }
    if (strcmp(key, "Reset Vector") == 0) {
        snprintf(state->status_value, sizeof(state->status_value), "0x%08X", state->profile->reset_vector);
        return state->status_value;
    }
    if (strcmp(key, "App2 Reset Vector") == 0) {
        snprintf(state->status_value, sizeof(state->status_value), "0x%08X", state->profile->app2_reset_vector);
        return state->status_value;
    }
    if (strcmp(key, "Initial SP") == 0) {
        snprintf(state->status_value, sizeof(state->status_value), "0x%08X", state->profile->initial_sp);
        return state->status_value;
    }
    if (strcmp(key, "App2 Initial SP") == 0) {
        snprintf(state->status_value, sizeof(state->status_value), "0x%08X", state->profile->app2_initial_sp);
        return state->status_value;
    }
    if (strcmp(key, "Boot Window Size") == 0) {
        snprintf(state->status_value, sizeof(state->status_value), "0x%X", state->profile->boot_window_size);
        return state->status_value;
    }
    if (strcmp(key, "App Window Size") == 0) {
        snprintf(state->status_value, sizeof(state->status_value), "0x%X", state->profile->app_window_size);
        return state->status_value;
    }
    if (strcmp(key, "App2 Window Size") == 0) {
        snprintf(state->status_value, sizeof(state->status_value), "0x%X", state->profile->app2_window_size);
        return state->status_value;
    }
    if (strcmp(key, "Secondary Role") == 0) {
        return state->profile->secondary_role;
    }
    if (strcmp(key, "Secondary Identity") == 0) {
        return state->profile->secondary_identity;
    }
    if (strcmp(key, "Primary Role") == 0) {
        return region_role(state, "app");
    }
    if (strcmp(key, "Execution Slot") == 0) {
        return slot_name_for_pc(state);
    }
    if (strcmp(key, "Execution Role") == 0) {
        return region_role(state, slot_name_for_pc(state));
    }
    if (strcmp(key, "Last Program Region") == 0) {
        return state->last_program_region;
    }
    if (strcmp(key, "Last Program Role") == 0) {
        return state->last_program_role;
    }
    if (strcmp(key, "Architecture") == 0) {
        return PK4_OBS_ARCH_CORTEX_M ? "arm-cortex-m" : "unknown";
    }
    return NULL;
}