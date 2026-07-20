#ifndef ZEPHYR_PICKIT4_REPLACEMENT_RI4_PROTOCOL_H_
#define ZEPHYR_PICKIT4_REPLACEMENT_RI4_PROTOCOL_H_

#include <stddef.h>
#include <stdint.h>

#include "device_state.h"

#define RI4_PACKET_SIZE 512U
#define RI4_HEADER_SIZE 16U
#define RI4_SIDE_EP_OUT 0x02U
#define RI4_SIDE_EP_IN 0x81U
#define RI4_DATA_EP_OUT 0x04U
#define RI4_DATA_EP_IN 0x83U
#define RI4_STREAM_EP_IN 0x03U

#define RI4_COMMAND_PROGRESS 0x84U
#define RI4_COMMAND_ABORT_READ 0x85U
#define RI4_COMMAND_NUCLEAR_RESET 0x86U
#define RI4_COMMAND_DETACH 0x87U

#define RI4_COMMAND_GET_STATUS_FROM_KEY 261U
#define RI4_SCRIPT_NO_DATA 256U
#define RI4_SCRIPT_WITH_DOWNLOAD 0xC0000101U
#define RI4_SCRIPT_WITH_UPLOAD 0x80000102U
#define RI4_SCRDONE 259U
#define RI4_RESULT_RESPONSE_TYPE 13U

struct ri4_header {
    uint32_t type;
    uint32_t seq;
    uint32_t bcount;
    uint32_t ocount;
};

struct ri4_response {
    uint8_t side_data[RI4_PACKET_SIZE];
    size_t side_length;
    uint8_t data_payload[RI4_PACKET_SIZE];
    size_t data_length;
};

int ri4_parse_header(const uint8_t *buffer, size_t length, struct ri4_header *header);
int ri4_build_result(uint32_t status, const uint8_t *payload, size_t payload_length, struct ri4_response *response);
int ri4_build_ack(uint32_t status, struct ri4_response *response);
int ri4_handle_side_packet(
    struct device_state *state,
    const uint8_t *buffer,
    size_t length,
    const uint8_t *download_payload,
    size_t download_length,
    struct ri4_response *response
);

#endif