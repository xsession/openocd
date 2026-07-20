#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>

#include "device_state.h"
#include "pk4_recovered_project.h"
#include "ri4_family_catalog.h"
#include "ri4_protocol.h"
#include "usb_transport.h"

LOG_MODULE_REGISTER(ri4_probe, LOG_LEVEL_INF);

static struct device_state g_state;
static struct pk4_recovered_project g_project;

static void log_catalog_summary(void)
{
    uint32_t preview = ri4_family_catalog_count < 3U ? ri4_family_catalog_count : 3U;
    uint32_t i;

    LOG_INF("RI4 catalog families: %u", (unsigned int)ri4_family_catalog_count);
    for (i = 0U; i < preview; ++i) {
        LOG_INF("Family[%u]: %s (%s)", (unsigned int)i, ri4_family_catalog[i].family, ri4_family_catalog[i].behavior);
    }
}

static void log_profile_summary(const struct device_state *state)
{
    const struct device_state_profile *profile = device_state_get_profile(state);

    LOG_INF("Observed probe profile: %s family=%s", profile->name, profile->family);
    LOG_INF("Observed boot/app/app2 base: 0x%08X / 0x%08X / 0x%08X", profile->boot_base, profile->app_base, profile->app2_base);
    LOG_INF("Observed reset vector=0x%08X SP=0x%08X boot-window=[0x%08X,+0x%X] app-window=[0x%08X,+0x%X] app2-window=[0x%08X,+0x%X]",
        profile->reset_vector,
        profile->initial_sp,
        profile->boot_base,
        profile->boot_window_size,
        profile->app_base,
        profile->app_window_size,
        profile->app2_base,
        profile->app2_window_size);
    LOG_INF("Observed app2 reset=0x%08X SP=0x%08X role=%s identity=%s",
        profile->app2_reset_vector,
        profile->app2_initial_sp,
        profile->secondary_role,
        profile->secondary_identity);
}

static void log_recovered_project_summary(const struct pk4_recovered_project *project)
{
    LOG_INF("Recovered project: %s family=%s", project->name, project->target_family);
    LOG_INF("Recovered slot %s base=0x%08X size=0x%X role=%s identity=%s",
        project->boot.name,
        project->boot.base,
        project->boot.window_size,
        project->boot.role,
        project->boot.identity);
    LOG_INF("Recovered slot %s base=0x%08X rv=0x%08X sp=0x%08X role=%s identity=%s",
        project->primary_app.name,
        project->primary_app.base,
        project->primary_app.reset_vector,
        project->primary_app.initial_sp,
        project->primary_app.role,
        project->primary_app.identity);
    LOG_INF("Recovered slot %s base=0x%08X rv=0x%08X sp=0x%08X role=%s identity=%s",
        project->secondary_app.name,
        project->secondary_app.base,
        project->secondary_app.reset_vector,
        project->secondary_app.initial_sp,
        project->secondary_app.role,
        project->secondary_app.identity);
}

void main(void)
{
    int rc;

    device_state_init(&g_state);
    pk4_recovered_project_init(&g_project, &g_state);
    log_catalog_summary();
    log_profile_summary(&g_state);
    log_recovered_project_summary(&g_project);

    LOG_INF("Zephyr RI4 probe scaffold started");
    LOG_INF("Expected endpoints side-out=0x%02X side-in=0x%02X data-out=0x%02X data-in=0x%02X stream-in=0x%02X",
        RI4_SIDE_EP_OUT,
        RI4_SIDE_EP_IN,
        RI4_DATA_EP_OUT,
        RI4_DATA_EP_IN,
        RI4_STREAM_EP_IN);

    rc = ri4_usb_transport_init(&g_state);
    if (rc == -ENOTSUP) {
        LOG_WRN("USB transport not enabled for this board/configuration");
    } else if (rc != 0) {
        LOG_ERR("USB transport init failed: %d", rc);
    }

    while (1) {
        k_sleep(K_SECONDS(1));
    }
}