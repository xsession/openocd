#ifndef ZEPHYR_PICKIT4_REPLACEMENT_SCRIPT_DISPATCH_H_
#define ZEPHYR_PICKIT4_REPLACEMENT_SCRIPT_DISPATCH_H_

#include <stddef.h>
#include <stdint.h>

#include "device_state.h"
#include "ri4_protocol.h"

struct script_dispatch_result {
    uint32_t status;
    uint8_t upload_data[RI4_PACKET_SIZE];
    size_t upload_length;
};

enum script_dispatch_mode {
    SCRIPT_DISPATCH_BASIC,
    SCRIPT_DISPATCH_UPLOAD,
    SCRIPT_DISPATCH_DOWNLOAD,
};

int script_dispatch_execute(
    struct device_state *state,
    enum script_dispatch_mode mode,
    const uint8_t *script_payload,
    size_t script_length,
    const uint8_t *download_payload,
    size_t download_length,
    size_t requested_upload_length,
    struct script_dispatch_result *result
);

#endif