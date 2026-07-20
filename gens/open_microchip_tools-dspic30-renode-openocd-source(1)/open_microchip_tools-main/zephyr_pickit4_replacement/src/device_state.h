#ifndef ZEPHYR_PICKIT4_REPLACEMENT_DEVICE_STATE_H_
#define ZEPHYR_PICKIT4_REPLACEMENT_DEVICE_STATE_H_

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define DEVICE_STATE_BOOT_WINDOW_SIZE (48U * 1024U)
#define DEVICE_STATE_APP_WINDOW_SIZE  (64U * 1024U)
#define DEVICE_STATE_APP2_WINDOW_SIZE (160U * 1024U)

struct device_state_profile {
    const char *name;
    const char *family;
    const char *secondary_role;
    const char *secondary_identity;
    uint32_t boot_base;
    uint32_t app_base;
    uint32_t app2_base;
    uint32_t initial_sp;
    uint32_t reset_vector;
    uint32_t app2_initial_sp;
    uint32_t app2_reset_vector;
    uint32_t boot_window_size;
    uint32_t app_window_size;
    uint32_t app2_window_size;
};

struct device_state {
    const struct device_state_profile *profile;
    bool debug_mode;
    bool halted;
    uint32_t pc;
    uint8_t boot_flash_window[DEVICE_STATE_BOOT_WINDOW_SIZE];
    uint8_t app_flash_window[DEVICE_STATE_APP_WINDOW_SIZE];
    uint8_t app2_flash_window[DEVICE_STATE_APP2_WINDOW_SIZE];
    char status_value[48];
    char last_program_region[16];
    char last_program_role[40];
};

void device_state_init(struct device_state *state);
void device_state_reset(struct device_state *state);
void device_state_halt(struct device_state *state);
void device_state_run(struct device_state *state);
void device_state_step(struct device_state *state);
void device_state_set_pc(struct device_state *state, uint32_t pc);
uint32_t device_state_get_pc(const struct device_state *state);
void device_state_erase_flash(struct device_state *state);
int device_state_write_flash(struct device_state *state, uint32_t address, const uint8_t *data, size_t size);
int device_state_read_flash(const struct device_state *state, uint32_t address, uint8_t *data, size_t size);
int device_state_write_primary_slot(struct device_state *state, uint32_t offset, const uint8_t *data, size_t size);
int device_state_read_primary_slot(const struct device_state *state, uint32_t offset, uint8_t *data, size_t size);
int device_state_write_secondary_slot(struct device_state *state, uint32_t offset, const uint8_t *data, size_t size);
int device_state_read_secondary_slot(const struct device_state *state, uint32_t offset, uint8_t *data, size_t size);
const struct device_state_profile *device_state_get_profile(const struct device_state *state);
const char *device_state_get_family(const struct device_state *state);
const char *device_state_get_profile_name(const struct device_state *state);
uint32_t device_state_get_boot_window_base(const struct device_state *state);
uint32_t device_state_get_boot_window_size(const struct device_state *state);
uint32_t device_state_get_app_window_base(const struct device_state *state);
uint32_t device_state_get_app_window_size(const struct device_state *state);
uint32_t device_state_get_app2_window_base(const struct device_state *state);
uint32_t device_state_get_app2_window_size(const struct device_state *state);
const char *device_state_get_status_value(struct device_state *state, const char *key);

#endif