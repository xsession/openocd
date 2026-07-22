// SPDX-License-Identifier: GPL-2.0-or-later

#ifdef HAVE_CONFIG_H
#include "config.h"
#endif

#include "usbasp.h"

#include <helper/command.h>
#include <helper/log.h>

#include <inttypes.h>
#include <stdbool.h>
#include <stdint.h>
#include <string.h>

#if defined(HAVE_LIBUSB1)
#include <jtag/drivers/libusb_helper.h>
#include <libusb.h>
#endif

const char avr_usbasp_backend_status[] = "isp-native";

#define USBASP_SHARED_VID		0x16c0
#define USBASP_SHARED_PID		0x05dc
#define USBASP_OLD_VID			0x03eb
#define USBASP_OLD_PID			0xc7b4

#define USBASP_FUNC_CONNECT		1
#define USBASP_FUNC_DISCONNECT		2
#define USBASP_FUNC_TRANSMIT		3
#define USBASP_FUNC_ENABLEPROG		5
#define USBASP_FUNC_GETCAPABILITIES	127

#define USBASP_CAP_TPI			0x01
#define USBASP_CAP_3MHZ			(1u << 24)

static const uint16_t usbasp_vids[] = {
	USBASP_SHARED_VID,
	USBASP_OLD_VID,
	0
};

static const uint16_t usbasp_pids[] = {
	USBASP_SHARED_PID,
	USBASP_OLD_PID,
	0
};

#if defined(HAVE_LIBUSB1)
static int avr_usbasp_transmit(struct libusb_device_handle *handle,
	bool receive, uint8_t function, const uint8_t send[4],
	uint8_t *buffer, uint16_t buffer_size, int *transferred)
{
	uint8_t request_type = LIBUSB_REQUEST_TYPE_VENDOR |
		LIBUSB_RECIPIENT_DEVICE;
	if (receive)
		request_type |= LIBUSB_ENDPOINT_IN;

	return jtag_libusb_control_transfer(handle, request_type, function,
		((uint16_t)send[1] << 8) | send[0],
		((uint16_t)send[3] << 8) | send[2],
		(char *)buffer, buffer_size, 5000, transferred);
}

static int avr_usbasp_open(struct libusb_device_handle **handle)
{
	return jtag_libusb_open(usbasp_vids, usbasp_pids, NULL, handle, NULL);
}

static int avr_usbasp_get_capabilities(struct libusb_device_handle *handle,
	uint32_t *capabilities, uint8_t response[4])
{
	uint8_t zeros[4] = { 0 };
	int transferred = 0;

	int retval = avr_usbasp_transmit(handle, true,
		USBASP_FUNC_GETCAPABILITIES, zeros, response, 4, &transferred);
	if (retval != ERROR_OK)
		return retval;

	*capabilities = 0;
	if (transferred == 4) {
		*capabilities = response[0] |
			((uint32_t)response[1] << 8) |
			((uint32_t)response[2] << 16) |
			((uint32_t)response[3] << 24);
	}

	return ERROR_OK;
}

static int avr_usbasp_connect_isp(struct libusb_device_handle *handle)
{
	uint8_t zeros[4] = { 0 };
	uint8_t response[4] = { 0 };
	int transferred = 0;

	int retval = avr_usbasp_transmit(handle, true, USBASP_FUNC_CONNECT,
		zeros, response, sizeof(response), &transferred);
	if (retval != ERROR_OK)
		return retval;

	alive_sleep(100);

	retval = avr_usbasp_transmit(handle, true, USBASP_FUNC_ENABLEPROG,
		zeros, response, sizeof(response), &transferred);
	if (retval != ERROR_OK)
		return retval;

	if (transferred != 1 || response[0] != 0)
		return ERROR_FAIL;

	return ERROR_OK;
}

static int avr_usbasp_spi(struct libusb_device_handle *handle,
	const uint8_t command[4], uint8_t response[4])
{
	int transferred = 0;
	int retval = avr_usbasp_transmit(handle, true, USBASP_FUNC_TRANSMIT,
		command, response, 4, &transferred);
	if (retval != ERROR_OK)
		return retval;
	if (transferred != 4)
		return ERROR_FAIL;

	return ERROR_OK;
}

static void avr_usbasp_disconnect(struct libusb_device_handle *handle)
{
	uint8_t zeros[4] = { 0 };
	int transferred;

	avr_usbasp_transmit(handle, true, USBASP_FUNC_DISCONNECT, zeros,
		zeros, sizeof(zeros), &transferred);
}

static int avr_usbasp_parse_byte(const char *text, uint8_t *out)
{
	unsigned int value;
	int retval = parse_uint(text, &value);
	if (retval != ERROR_OK)
		return retval;

	if (value > UINT8_MAX)
		return ERROR_COMMAND_ARGUMENT_INVALID;

	*out = value;
	return ERROR_OK;
}

COMMAND_HANDLER(handle_avr_usbasp_probe_command)
{
	if (CMD_ARGC != 0)
		return ERROR_COMMAND_SYNTAX_ERROR;

	struct libusb_device_handle *handle;
	int retval = avr_usbasp_open(&handle);
	if (retval != ERROR_OK) {
		command_print(CMD, "USBasp probe: no device opened");
		command_print(CMD, "Expected VID/PID: 16c0:05dc or 03eb:c7b4");
		return retval;
	}

	uint8_t response[4] = { 0 };
	uint32_t capabilities = 0;

	retval = avr_usbasp_get_capabilities(handle, &capabilities, response);
	if (retval != ERROR_OK) {
		command_print(CMD, "USBasp probe: opened device but capability request failed");
		avr_usbasp_disconnect(handle);
		jtag_libusb_close(handle);
		return retval;
	}

	command_print(CMD, "USBasp probe: opened");
	command_print(CMD, "capability bytes: %02x %02x %02x %02x",
		response[0], response[1], response[2], response[3]);
	command_print(CMD, "capabilities: 0x%08" PRIx32, capabilities);
	command_print(CMD, "tpi: %s",
		(capabilities & USBASP_CAP_TPI) ? "yes" : "no");
	command_print(CMD, "sck_3mhz: %s",
		(capabilities & USBASP_CAP_3MHZ) ? "yes" : "no");

	avr_usbasp_disconnect(handle);
	jtag_libusb_close(handle);

	return ERROR_OK;
}

COMMAND_HANDLER(handle_avr_usbasp_spi_command)
{
	if (CMD_ARGC != 4)
		return ERROR_COMMAND_SYNTAX_ERROR;

	uint8_t command[4];
	for (unsigned int i = 0; i < 4; i++) {
		int retval = avr_usbasp_parse_byte(CMD_ARGV[i], &command[i]);
		if (retval != ERROR_OK) {
			command_print(CMD, "byte%u value ('%s') is not valid",
				i, CMD_ARGV[i]);
			return retval;
		}
	}

	struct libusb_device_handle *handle;
	int retval = avr_usbasp_open(&handle);
	if (retval != ERROR_OK) {
		command_print(CMD, "USBasp SPI: no device opened");
		return retval;
	}

	retval = avr_usbasp_connect_isp(handle);
	if (retval != ERROR_OK) {
		command_print(CMD, "USBasp SPI: target did not enter ISP programming mode");
		avr_usbasp_disconnect(handle);
		jtag_libusb_close(handle);
		return retval;
	}

	uint8_t response[4] = { 0 };
	retval = avr_usbasp_spi(handle, command, response);
	if (retval == ERROR_OK)
		command_print(CMD, "response: %02x %02x %02x %02x",
			response[0], response[1], response[2], response[3]);

	avr_usbasp_disconnect(handle);
	jtag_libusb_close(handle);

	return retval;
}

COMMAND_HANDLER(handle_avr_usbasp_signature_command)
{
	if (CMD_ARGC != 0)
		return ERROR_COMMAND_SYNTAX_ERROR;

	struct libusb_device_handle *handle;
	int retval = avr_usbasp_open(&handle);
	if (retval != ERROR_OK) {
		command_print(CMD, "USBasp signature: no device opened");
		return retval;
	}

	retval = avr_usbasp_connect_isp(handle);
	if (retval != ERROR_OK) {
		command_print(CMD, "USBasp signature: target did not enter ISP programming mode");
		avr_usbasp_disconnect(handle);
		jtag_libusb_close(handle);
		return retval;
	}

	uint8_t signature[3] = { 0 };
	for (uint8_t i = 0; i < 3; i++) {
		uint8_t command[4] = { 0x30, 0x00, i, 0x00 };
		uint8_t response[4] = { 0 };

		retval = avr_usbasp_spi(handle, command, response);
		if (retval != ERROR_OK)
			break;

		signature[i] = response[3];
	}

	if (retval == ERROR_OK)
		command_print(CMD, "signature: %02x %02x %02x",
			signature[0], signature[1], signature[2]);

	avr_usbasp_disconnect(handle);
	jtag_libusb_close(handle);

	return retval;
}
#else
COMMAND_HANDLER(handle_avr_usbasp_probe_command)
{
	if (CMD_ARGC != 0)
		return ERROR_COMMAND_SYNTAX_ERROR;

	command_print(CMD, "USBasp probe unavailable: OpenOCD was built without libusb-1.0");
	return ERROR_FAIL;
}

COMMAND_HANDLER(handle_avr_usbasp_spi_command)
{
	if (CMD_ARGC != 4)
		return ERROR_COMMAND_SYNTAX_ERROR;

	command_print(CMD, "USBasp SPI unavailable: OpenOCD was built without libusb-1.0");
	return ERROR_FAIL;
}

COMMAND_HANDLER(handle_avr_usbasp_signature_command)
{
	if (CMD_ARGC != 0)
		return ERROR_COMMAND_SYNTAX_ERROR;

	command_print(CMD, "USBasp signature unavailable: OpenOCD was built without libusb-1.0");
	return ERROR_FAIL;
}
#endif

static const struct command_registration avr_usbasp_command_handlers[] = {
	{
		.name = "probe",
		.handler = handle_avr_usbasp_probe_command,
		.mode = COMMAND_ANY,
		.help = "open a USBasp programmer and read firmware capabilities",
		.usage = "",
	},
	{
		.name = "spi",
		.handler = handle_avr_usbasp_spi_command,
		.mode = COMMAND_ANY,
		.help = "send one raw 4-byte AVR ISP command through USBasp",
		.usage = "byte0 byte1 byte2 byte3",
	},
	{
		.name = "signature",
		.handler = handle_avr_usbasp_signature_command,
		.mode = COMMAND_ANY,
		.help = "read the AVR three-byte device signature through USBasp ISP",
		.usage = "",
	},
	COMMAND_REGISTRATION_DONE
};

static const struct command_registration avr_usbasp_commands[] = {
	{
		.name = "usbasp",
		.mode = COMMAND_ANY,
		.help = "native USBasp programmer transport",
		.usage = "",
		.chain = avr_usbasp_command_handlers,
	},
	COMMAND_REGISTRATION_DONE
};

int avr_usbasp_register_commands(struct command_context *cmd_ctx)
{
	return register_commands(cmd_ctx, "avr", avr_usbasp_commands);
}
