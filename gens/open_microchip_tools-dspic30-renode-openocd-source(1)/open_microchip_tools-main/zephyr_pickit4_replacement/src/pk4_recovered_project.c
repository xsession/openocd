#include "pk4_recovered_project.h"

#include <errno.h>

static const char *const g_boot_role = "boot strap slot";
static const char *const g_primary_role = "RI4 host-facing app slot";
static const char *const g_boot_identity = "PK4 observed boot image";
static const char *const g_primary_identity = "PK4 observed primary RI4 app";

void pk4_recovered_project_init(struct pk4_recovered_project *project, const struct device_state *state)
{
    const struct device_state_profile *profile = device_state_get_profile(state);

    project->name = "pk4_cleanroom_recovery_project";
    project->target_family = profile->family;
    project->boot.kind = PK4_RECOVERED_SLOT_BOOT;
    project->boot.name = "boot";
    project->boot.role = g_boot_role;
    project->boot.identity = g_boot_identity;
    project->boot.base = profile->boot_base;
    project->boot.window_size = profile->boot_window_size;
    project->boot.initial_sp = 0U;
    project->boot.reset_vector = 0U;

    project->primary_app.kind = PK4_RECOVERED_SLOT_PRIMARY_APP;
    project->primary_app.name = "app";
    project->primary_app.role = g_primary_role;
    project->primary_app.identity = g_primary_identity;
    project->primary_app.base = profile->app_base;
    project->primary_app.window_size = profile->app_window_size;
    project->primary_app.initial_sp = profile->initial_sp;
    project->primary_app.reset_vector = profile->reset_vector;

    project->secondary_app.kind = PK4_RECOVERED_SLOT_SECONDARY_APP;
    project->secondary_app.name = "app2";
    project->secondary_app.role = profile->secondary_role;
    project->secondary_app.identity = profile->secondary_identity;
    project->secondary_app.base = profile->app2_base;
    project->secondary_app.window_size = profile->app2_window_size;
    project->secondary_app.initial_sp = profile->app2_initial_sp;
    project->secondary_app.reset_vector = profile->app2_reset_vector;
}

const struct pk4_recovered_slot_descriptor *pk4_recovered_project_get_slot(
    const struct pk4_recovered_project *project,
    enum pk4_recovered_slot_kind kind
)
{
    switch (kind) {
    case PK4_RECOVERED_SLOT_BOOT:
        return &project->boot;
    case PK4_RECOVERED_SLOT_PRIMARY_APP:
        return &project->primary_app;
    case PK4_RECOVERED_SLOT_SECONDARY_APP:
        return &project->secondary_app;
    default:
        return NULL;
    }
}

int pk4_recovered_project_write_slot(
    struct device_state *state,
    enum pk4_recovered_slot_kind kind,
    uint32_t offset,
    const uint8_t *data,
    size_t size
)
{
    switch (kind) {
    case PK4_RECOVERED_SLOT_BOOT:
        return device_state_write_flash(state, device_state_get_boot_window_base(state) + offset, data, size);
    case PK4_RECOVERED_SLOT_PRIMARY_APP:
        return device_state_write_primary_slot(state, offset, data, size);
    case PK4_RECOVERED_SLOT_SECONDARY_APP:
        return device_state_write_secondary_slot(state, offset, data, size);
    default:
        return -EINVAL;
    }
}

int pk4_recovered_project_read_slot(
    const struct device_state *state,
    enum pk4_recovered_slot_kind kind,
    uint32_t offset,
    uint8_t *data,
    size_t size
)
{
    switch (kind) {
    case PK4_RECOVERED_SLOT_BOOT:
        return device_state_read_flash(state, device_state_get_boot_window_base(state) + offset, data, size);
    case PK4_RECOVERED_SLOT_PRIMARY_APP:
        return device_state_read_primary_slot(state, offset, data, size);
    case PK4_RECOVERED_SLOT_SECONDARY_APP:
        return device_state_read_secondary_slot(state, offset, data, size);
    default:
        return -EINVAL;
    }
}