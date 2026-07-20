#include "ri4_protocol.h"

#include <errno.h>
#include <string.h>

#include <zephyr/kernel.h>

#include "script_dispatch.h"

static uint32_t read_le32(const uint8_t *buffer)
{
    return ((uint32_t)buffer[0]) |
           ((uint32_t)buffer[1] << 8) |
           ((uint32_t)buffer[2] << 16) |
           ((uint32_t)buffer[3] << 24);
}

static void write_le32(uint8_t *buffer, uint32_t value)
{
    buffer[0] = (uint8_t)(value & 0xFFU);
    buffer[1] = (uint8_t)((value >> 8) & 0xFFU);
    buffer[2] = (uint8_t)((value >> 16) & 0xFFU);
    buffer[3] = (uint8_t)((value >> 24) & 0xFFU);
}

static bool append_status_string(const char *value, struct ri4_response *response)
{
    size_t length = strlen(value) + 1U;

    if ((RI4_HEADER_SIZE + length) > sizeof(response->side_data)) {
        return false;
    }
    memset(response, 0, sizeof(*response));
    write_le32(&response->side_data[0], RI4_COMMAND_GET_STATUS_FROM_KEY);
    write_le32(&response->side_data[4], 0U);
    write_le32(&response->side_data[8], (uint32_t)(RI4_HEADER_SIZE + length));
    write_le32(&response->side_data[12], 0U);
    memcpy(&response->side_data[RI4_HEADER_SIZE], value, length);
    response->side_length = RI4_HEADER_SIZE + length;
    return true;
}

static const char *status_value_for_key(struct device_state *state, const uint8_t *payload, size_t payload_length)
{
    size_t key_length = strnlen((const char *)payload, payload_length);
    const char *profile_value;

    if (key_length == 0U) {
        return "unsupported";
    }
    if ((key_length == 20U) && (strncmp((const char *)payload, "Commands in progress", 20) == 0)) {
        return "0";
    }
    if ((key_length == 10U) && (strncmp((const char *)payload, "Debug Mode", 10) == 0)) {
        return state->debug_mode ? "1" : "0";
    }
    if ((key_length == 13U) && (strncmp((const char *)payload, "Target Halted", 13) == 0)) {
        return state->halted ? "1" : "0";
    }
    profile_value = device_state_get_status_value(state, (const char *)payload);
    if (profile_value != NULL) {
        return profile_value;
    }
    return "unsupported";
}

int ri4_parse_header(const uint8_t *buffer, size_t length, struct ri4_header *header)
{
    if (length < RI4_HEADER_SIZE) {
        return -1;
    }

    header->type = read_le32(&buffer[0]);
    header->seq = read_le32(&buffer[4]);
    header->bcount = read_le32(&buffer[8]);
    header->ocount = read_le32(&buffer[12]);
    return 0;
}

int ri4_build_result(uint32_t status, const uint8_t *payload, size_t payload_length, struct ri4_response *response)
{
    size_t total = RI4_HEADER_SIZE;

    memset(response, 0, sizeof(*response));
    if (payload != NULL && payload_length > 0U) {
        total += 8U + payload_length;
    }
    if (total > sizeof(response->side_data)) {
        return -1;
    }

    write_le32(&response->side_data[0], RI4_RESULT_RESPONSE_TYPE);
    write_le32(&response->side_data[4], 0U);
    write_le32(&response->side_data[8], (uint32_t)total);
    write_le32(&response->side_data[12], 0U);

    if (payload != NULL && payload_length > 0U) {
        write_le32(&response->side_data[16], status);
        write_le32(&response->side_data[20], (uint32_t)payload_length);
        memcpy(&response->side_data[24], payload, payload_length);
    }

    response->side_length = total;
    return 0;
}

int ri4_build_ack(uint32_t status, struct ri4_response *response)
{
    memset(response, 0, sizeof(*response));
    write_le32(&response->side_data[0], RI4_RESULT_RESPONSE_TYPE);
    write_le32(&response->side_data[4], 0U);
    write_le32(&response->side_data[8], status == 0U ? 16U : 20U);
    write_le32(&response->side_data[12], 0U);
    if (status != 0U) {
        write_le32(&response->side_data[16], status);
        response->side_length = 20U;
    } else {
        response->side_length = 16U;
    }
    return 0;
}

int ri4_handle_side_packet(
    struct device_state *state,
    const uint8_t *buffer,
    size_t length,
    const uint8_t *download_payload,
    size_t download_length,
    struct ri4_response *response
)
{
    struct ri4_header header;
    struct script_dispatch_result dispatch_result;
    const uint8_t *script_payload;
    size_t script_length;

    if (ri4_parse_header(buffer, length, &header) != 0) {
        return -EINVAL;
    }

    if (header.bcount < RI4_HEADER_SIZE || header.bcount > length) {
        return -EINVAL;
    }

    script_payload = &buffer[RI4_HEADER_SIZE];
    script_length = header.bcount - RI4_HEADER_SIZE;

    switch (header.type) {
    case RI4_SCRIPT_NO_DATA:
        if (script_dispatch_execute(state, SCRIPT_DISPATCH_BASIC, script_payload, script_length, NULL, 0U, 0U, &dispatch_result) != 0) {
            return ri4_build_result(dispatch_result.status, NULL, 0U, response);
        }
        return ri4_build_result(dispatch_result.status, NULL, 0U, response);
    case RI4_SCRIPT_WITH_DOWNLOAD:
        if (script_dispatch_execute(state, SCRIPT_DISPATCH_DOWNLOAD, script_payload, script_length, download_payload, download_length, 0U, &dispatch_result) != 0) {
            return ri4_build_ack(dispatch_result.status, response);
        }
        return ri4_build_ack(dispatch_result.status, response);
    case RI4_SCRIPT_WITH_UPLOAD:
        if (script_dispatch_execute(state, SCRIPT_DISPATCH_UPLOAD, script_payload, script_length, NULL, 0U, header.ocount, &dispatch_result) != 0) {
            return ri4_build_result(dispatch_result.status, NULL, 0U, response);
        }
        memcpy(response->data_payload, dispatch_result.upload_data, dispatch_result.upload_length);
        response->data_length = dispatch_result.upload_length;
        return ri4_build_ack(dispatch_result.status, response);
    case RI4_SCRDONE:
        return ri4_build_result(0U, NULL, 0U, response);
    case RI4_COMMAND_GET_STATUS_FROM_KEY:
        if (!append_status_string(status_value_for_key(state, script_payload, script_length), response)) {
            return -ENOMEM;
        }
        return 0;
    default:
        return ri4_build_result(1U, NULL, 0U, response);
    }
}