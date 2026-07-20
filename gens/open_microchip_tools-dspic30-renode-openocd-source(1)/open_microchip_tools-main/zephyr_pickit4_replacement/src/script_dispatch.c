#include "script_dispatch.h"

#include <errno.h>
#include <string.h>

#include <zephyr/logging/log.h>

#include "ri4_family_catalog.h"

LOG_MODULE_REGISTER(script_dispatch, LOG_LEVEL_INF);

#define STUB_MAGIC0 0x5AU
#define STUB_MAGIC1 0xA5U

enum stub_script_opcode {
    STUB_OP_ENTER_DEBUG_MODE = 0x10,
    STUB_OP_GET_PC = 0x11,
    STUB_OP_SET_PC = 0x12,
    STUB_OP_RUN = 0x13,
    STUB_OP_HALT = 0x14,
    STUB_OP_SINGLE_STEP = 0x15,
    STUB_OP_SINGLE_STEP_UFEX = 0x16,
    STUB_OP_ERASE_CHIP = 0x20,
    STUB_OP_WRITE_PROGMEM = 0x21,
    STUB_OP_READ_PROGMEM = 0x22,
    STUB_OP_WRITE_PRIMARY_SLOT = 0x23,
    STUB_OP_READ_PRIMARY_SLOT = 0x24,
    STUB_OP_WRITE_SECONDARY_SLOT = 0x25,
    STUB_OP_READ_SECONDARY_SLOT = 0x26,
    STUB_OP_ENTER_TMOD_LV = 0x30,
    STUB_OP_EXIT_TMOD = 0x31,
    STUB_OP_NOOP = 0x7F,
};

struct script_call {
    uint32_t param_size;
    uint32_t script_size;
    const uint8_t *params;
    const uint8_t *script_bytes;
};

static uint32_t read_le32(const uint8_t *buffer)
{
    return ((uint32_t)buffer[0]) |
           ((uint32_t)buffer[1] << 8) |
           ((uint32_t)buffer[2] << 16) |
           ((uint32_t)buffer[3] << 24);
}

static int parse_script_call(const uint8_t *payload, size_t payload_length, struct script_call *call)
{
    if (payload_length < 8U) {
        return -EINVAL;
    }
    call->param_size = read_le32(payload);
    call->script_size = read_le32(payload + 4U);
    if ((size_t)(8U + call->param_size + call->script_size) > payload_length) {
        return -EINVAL;
    }
    call->params = payload + 8U;
    call->script_bytes = call->params + call->param_size;
    return 0;
}

static uint8_t detect_opcode(const struct script_call *call)
{
    if (call->script_size >= 3U &&
        call->script_bytes[0] == STUB_MAGIC0 &&
        call->script_bytes[1] == STUB_MAGIC1) {
        return call->script_bytes[2];
    }
    return STUB_OP_NOOP;
}

static uint32_t first_param_u32(const struct script_call *call, uint32_t fallback)
{
    if (call->param_size < 4U) {
        return fallback;
    }
    return read_le32(call->params);
}

static uint32_t second_param_u32(const struct script_call *call, uint32_t fallback)
{
    if (call->param_size < 8U) {
        return fallback;
    }
    return read_le32(call->params + 4U);
}

static void erase_flash(struct device_state *state)
{
    device_state_erase_flash(state);
}

static void seed_default_upload(struct device_state *state, size_t requested_upload_length, struct script_dispatch_result *result)
{
    size_t produced = requested_upload_length;

    if (produced > sizeof(result->upload_data)) {
        produced = sizeof(result->upload_data);
    }

    memset(result->upload_data, 0, produced);
    if (produced >= sizeof(uint32_t)) {
        uint32_t pc = device_state_get_pc(state);
        memcpy(result->upload_data, &pc, sizeof(pc));
    }
    result->upload_length = produced;
}

int script_dispatch_execute(
    struct device_state *state,
    enum script_dispatch_mode mode,
    const uint8_t *script_payload,
    size_t script_length,
    const uint8_t *download_payload,
    size_t download_length,
    size_t requested_upload_length,
    struct script_dispatch_result *result
)
{
    struct script_call call;
    uint8_t opcode;
    uint32_t address;
    uint32_t size;

    memset(result, 0, sizeof(*result));

    if (parse_script_call(script_payload, script_length, &call) != 0) {
        result->status = 1U;
        return -EINVAL;
    }

    opcode = detect_opcode(&call);

    switch (opcode) {
    case STUB_OP_ENTER_DEBUG_MODE:
    case STUB_OP_ENTER_TMOD_LV:
        device_state_halt(state);
        return 0;
    case STUB_OP_EXIT_TMOD:
        device_state_run(state);
        return 0;
    case STUB_OP_GET_PC:
        if (mode != SCRIPT_DISPATCH_UPLOAD) {
            result->status = 1U;
            return -EINVAL;
        }
        seed_default_upload(state, requested_upload_length, result);
        return 0;
    case STUB_OP_SET_PC:
        device_state_set_pc(state, first_param_u32(&call, 0U));
        device_state_halt(state);
        return 0;
    case STUB_OP_RUN:
        device_state_run(state);
        return 0;
    case STUB_OP_HALT:
        device_state_halt(state);
        return 0;
    case STUB_OP_SINGLE_STEP:
    case STUB_OP_SINGLE_STEP_UFEX:
        device_state_step(state);
        return 0;
    case STUB_OP_ERASE_CHIP:
        erase_flash(state);
        return 0;
    case STUB_OP_WRITE_PROGMEM:
        if (mode != SCRIPT_DISPATCH_DOWNLOAD || download_payload == NULL) {
            result->status = 1U;
            return -EINVAL;
        }
        address = first_param_u32(&call, 0U);
        if (device_state_write_flash(state, address, download_payload, download_length) != 0) {
            result->status = 1U;
            return -EINVAL;
        }
        LOG_INF("%s WriteProgmem addr=0x%08X size=%u region=%s role=%s",
            device_state_get_profile_name(state),
            (unsigned int)address,
            (unsigned int)download_length,
            device_state_get_status_value(state, "Last Program Region"),
            device_state_get_status_value(state, "Last Program Role"));
        return 0;
    case STUB_OP_READ_PROGMEM:
        if (mode != SCRIPT_DISPATCH_UPLOAD) {
            result->status = 1U;
            return -EINVAL;
        }
        address = first_param_u32(&call, 0U);
        size = second_param_u32(&call, (uint32_t)requested_upload_length);
        if (size > sizeof(result->upload_data)) {
            size = sizeof(result->upload_data);
        }
        if (device_state_read_flash(state, address, result->upload_data, size) != 0) {
            result->status = 1U;
            return -EINVAL;
        }
        result->upload_length = size;
        return 0;
    case STUB_OP_WRITE_PRIMARY_SLOT:
        if (mode != SCRIPT_DISPATCH_DOWNLOAD || download_payload == NULL) {
            result->status = 1U;
            return -EINVAL;
        }
        address = first_param_u32(&call, 0U);
        if (device_state_write_primary_slot(state, address, download_payload, download_length) != 0) {
            result->status = 1U;
            return -EINVAL;
        }
        LOG_INF("%s WritePrimarySlot offset=0x%08X size=%u role=%s",
            device_state_get_profile_name(state),
            (unsigned int)address,
            (unsigned int)download_length,
            device_state_get_status_value(state, "Primary Role"));
        return 0;
    case STUB_OP_READ_PRIMARY_SLOT:
        if (mode != SCRIPT_DISPATCH_UPLOAD) {
            result->status = 1U;
            return -EINVAL;
        }
        address = first_param_u32(&call, 0U);
        size = second_param_u32(&call, (uint32_t)requested_upload_length);
        if (size > sizeof(result->upload_data)) {
            size = sizeof(result->upload_data);
        }
        if (device_state_read_primary_slot(state, address, result->upload_data, size) != 0) {
            result->status = 1U;
            return -EINVAL;
        }
        result->upload_length = size;
        return 0;
    case STUB_OP_WRITE_SECONDARY_SLOT:
        if (mode != SCRIPT_DISPATCH_DOWNLOAD || download_payload == NULL) {
            result->status = 1U;
            return -EINVAL;
        }
        address = first_param_u32(&call, 0U);
        if (device_state_write_secondary_slot(state, address, download_payload, download_length) != 0) {
            result->status = 1U;
            return -EINVAL;
        }
        LOG_INF("%s WriteSecondarySlot offset=0x%08X size=%u role=%s",
            device_state_get_profile_name(state),
            (unsigned int)address,
            (unsigned int)download_length,
            device_state_get_status_value(state, "Secondary Role"));
        return 0;
    case STUB_OP_READ_SECONDARY_SLOT:
        if (mode != SCRIPT_DISPATCH_UPLOAD) {
            result->status = 1U;
            return -EINVAL;
        }
        address = first_param_u32(&call, 0U);
        size = second_param_u32(&call, (uint32_t)requested_upload_length);
        if (size > sizeof(result->upload_data)) {
            size = sizeof(result->upload_data);
        }
        if (device_state_read_secondary_slot(state, address, result->upload_data, size) != 0) {
            result->status = 1U;
            return -EINVAL;
        }
        result->upload_length = size;
        return 0;
    case STUB_OP_NOOP:
    default:
        break;
    }

    if (mode == SCRIPT_DISPATCH_DOWNLOAD && download_payload != NULL && download_length > 0U) {
        if (device_state_write_flash(state, device_state_get_app_window_base(state), download_payload, download_length) != 0) {
            result->status = 1U;
            return -1;
        }
        LOG_INF("Accepted %u bytes of mock program data at app base 0x%08X role=%s",
            (unsigned int)download_length,
            (unsigned int)device_state_get_app_window_base(state),
            device_state_get_status_value(state, "Primary Role"));
        return 0;
    }

    if (mode == SCRIPT_DISPATCH_UPLOAD) {
        seed_default_upload(state, requested_upload_length, result);
        LOG_INF("Returning %u bytes of mock upload data", (unsigned int)result->upload_length);
        return 0;
    }

    LOG_INF("Stub basic script executed for %s; catalog families=%u", device_state_get_family(state), (unsigned int)ri4_family_catalog_count);
    device_state_halt(state);
    return 0;
}