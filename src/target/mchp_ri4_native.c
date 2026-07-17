// SPDX-License-Identifier: GPL-2.0-or-later
/* Native Microchip RI4 USB transport and script executor. */

#ifdef HAVE_CONFIG_H
#include "config.h"
#endif

#include "mchp_ri4_native.h"

#include <helper/log.h>
#include <helper/replacements.h>
#include <target/target.h>

#include <ctype.h>
#include <errno.h>
#include <inttypes.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifdef HAVE_LIBUSB1
#include <libusb.h>
#endif
#ifdef HAVE_ZLIB
#include <zlib.h>
#endif

#define RI4_SIDE_OUT 0x02
#define RI4_SIDE_IN 0x81
#define RI4_DATA_OUT 0x04
#define RI4_DATA_IN 0x83
#define RI4_INTERFACE 0
#define RI4_HEADER_SIZE 16U
#define RI4_REPLY_SIZE 1024U
#define RI4_FAST_TIMEOUT 10000U
#define RI4_DATA_TIMEOUT 30000U
#define RI4_CATALOG_LIMIT (512U * 1024U * 1024U)

#define RI4_SCRIPT_NO_DATA 0x00000100U
#define RI4_SCRIPT_DOWNLOAD 0xc0000101U
#define RI4_SCRIPT_UPLOAD 0x80000102U
#define RI4_SCRIPT_DONE 0x00000103U
#define RI4_RESULT 0x0000000dU
#define RI4_GET_STATUS_FROM_KEY 261U
#define RI4_ABORT_SCRIPTING_ENGINE 263U
#define RI4_FLUSH_DOWNLOAD 272U
#define RI4_FLUSH_UPLOAD 273U
#define RI4_NUCLEAR_RESET 0x86U

struct ri4_script {
	char *name;
	uint8_t *data;
	size_t length;
	struct ri4_script *next;
};

struct mchp_ri4_native {
#ifdef HAVE_LIBUSB1
	libusb_context *usb_context;
	libusb_device_handle *usb;
#endif
	struct ri4_script *scripts;
	char *processor;
	char *family;
	char *suffix;
};

static uint32_t ri4_get_u32(const uint8_t *buffer)
{
	return (uint32_t)buffer[0] | ((uint32_t)buffer[1] << 8) |
		((uint32_t)buffer[2] << 16) | ((uint32_t)buffer[3] << 24);
}

static void ri4_put_u32(uint8_t *buffer, uint32_t value)
{
	buffer[0] = value;
	buffer[1] = value >> 8;
	buffer[2] = value >> 16;
	buffer[3] = value >> 24;
}

static bool ri4_ends_with(const char *value, const char *suffix)
{
	size_t value_len = strlen(value);
	size_t suffix_len = strlen(suffix);
	return value_len >= suffix_len &&
		strcasecmp(value + value_len - suffix_len, suffix) == 0;
}

static int ri4_read_catalog(const char *path, char **text_out, size_t *length_out)
{
	char *buffer = NULL;
	size_t used = 0;
	size_t allocated = 0;

	if (ri4_ends_with(path, ".gz")) {
#ifdef HAVE_ZLIB
		gzFile file = gzopen(path, "rb");
		if (!file) {
			LOG_ERROR("mchp_ri4: cannot open compressed script catalog '%s'", path);
			return ERROR_FAIL;
		}
		allocated = 1024U * 1024U;
		buffer = malloc(allocated + 1U);
		if (!buffer) {
			gzclose(file);
			return ERROR_FAIL;
		}
		while (true) {
			if (used == allocated) {
				if (allocated >= RI4_CATALOG_LIMIT) {
					LOG_ERROR("mchp_ri4: decompressed script catalog exceeds 512 MiB");
					free(buffer);
					gzclose(file);
					return ERROR_FAIL;
				}
				allocated = MIN(allocated * 2U, RI4_CATALOG_LIMIT);
				char *grown = realloc(buffer, allocated + 1U);
				if (!grown) {
					free(buffer);
					gzclose(file);
					return ERROR_FAIL;
				}
				buffer = grown;
			}
			int count = gzread(file, buffer + used,
				(unsigned int)MIN(allocated - used, (size_t)INT_MAX));
			if (count < 0) {
				int error_number;
				LOG_ERROR("mchp_ri4: cannot decompress '%s': %s", path,
					gzerror(file, &error_number));
				free(buffer);
				gzclose(file);
				return ERROR_FAIL;
			}
			if (count == 0)
				break;
			used += (size_t)count;
		}
		gzclose(file);
#else
		LOG_ERROR("mchp_ri4: '%s' is gzip-compressed, but OpenOCD was built without zlib", path);
		return ERROR_FAIL;
#endif
	} else {
		FILE *file = fopen(path, "rb");
		if (!file) {
			LOG_ERROR("mchp_ri4: cannot open script catalog '%s': %s", path, strerror(errno));
			return ERROR_FAIL;
		}
		if (fseek(file, 0, SEEK_END) != 0) {
			fclose(file);
			return ERROR_FAIL;
		}
		long file_size = ftell(file);
		if (file_size < 0 || (unsigned long)file_size > RI4_CATALOG_LIMIT ||
				fseek(file, 0, SEEK_SET) != 0) {
			fclose(file);
			return ERROR_FAIL;
		}
		used = (size_t)file_size;
		buffer = malloc(used + 1U);
		if (!buffer) {
			fclose(file);
			return ERROR_FAIL;
		}
		if (used && fread(buffer, 1, used, file) != used) {
			free(buffer);
			fclose(file);
			return ERROR_FAIL;
		}
		fclose(file);
	}

	buffer[used] = '\0';
	*text_out = buffer;
	*length_out = used;
	return ERROR_OK;
}

static char *ri4_trim(char *text)
{
	while (isspace((unsigned char)*text))
		text++;
	char *end = text + strlen(text);
	while (end > text && isspace((unsigned char)end[-1]))
		*--end = '\0';
	if (end > text + 1 && ((*text == '"' && end[-1] == '"') ||
			(*text == '\'' && end[-1] == '\''))) {
		text++;
		end[-1] = '\0';
	}
	return text;
}

static int ri4_append_byte(uint8_t **data, size_t *used, size_t *allocated,
	const char *value)
{
	char *end = NULL;
	errno = 0;
	unsigned long parsed = strtoul(value, &end, 0);
	if (errno || end == value || (*end && !isspace((unsigned char)*end)) || parsed > UINT8_MAX)
		return ERROR_FAIL;
	if (*used == *allocated) {
		size_t next = *allocated ? *allocated * 2U : 256U;
		uint8_t *grown = realloc(*data, next);
		if (!grown)
			return ERROR_FAIL;
		*data = grown;
		*allocated = next;
	}
	(*data)[(*used)++] = (uint8_t)parsed;
	return ERROR_OK;
}

static int ri4_add_script(struct mchp_ri4_native *session, const char *name,
	const char *processor, uint8_t *data, size_t length)
{
	if (!name || !processor || strcasecmp(processor, session->processor) != 0 || !length) {
		free(data);
		return ERROR_OK;
	}
	struct ri4_script *script = calloc(1, sizeof(*script));
	if (!script) {
		free(data);
		return ERROR_FAIL;
	}
	script->name = strdup(name);
	if (!script->name) {
		free(data);
		free(script);
		return ERROR_FAIL;
	}
	script->data = data;
	script->length = length;
	script->next = session->scripts;
	session->scripts = script;
	return ERROR_OK;
}

static int ri4_parse_yaml(struct mchp_ri4_native *session, char *text)
{
	char *name = NULL;
	char *processor = NULL;
	uint8_t *bytes = NULL;
	size_t byte_count = 0;
	size_t byte_space = 0;
	enum { FIELD_NONE, FIELD_FUNCTION, FIELD_PROCESSOR, FIELD_BYTES } field = FIELD_NONE;
	char *save = NULL;

	for (char *line = strtok_r(text, "\n", &save); line; line = strtok_r(NULL, "\n", &save)) {
		char *trimmed = ri4_trim(line);
		if (strcmp(trimmed, "function:") == 0) {
			if (name) {
				int result = ri4_add_script(session, name, processor, bytes, byte_count);
				if (result != ERROR_OK) {
					free(name);
					free(processor);
					return result;
				}
				free(name);
				free(processor);
				name = NULL;
				processor = NULL;
				bytes = NULL;
				byte_count = byte_space = 0;
			}
			field = FIELD_FUNCTION;
		} else if (strcmp(trimmed, "processor:") == 0) {
			field = FIELD_PROCESSOR;
		} else if (strcmp(trimmed, "scrbytes:") == 0) {
			field = FIELD_BYTES;
		} else if (strncmp(trimmed, "text:", 5) == 0) {
			char *value = ri4_trim(trimmed + 5);
			if (field == FIELD_FUNCTION && !name) {
				name = strdup(value);
				field = FIELD_NONE;
			} else if (field == FIELD_PROCESSOR && !processor) {
				processor = strdup(value);
				field = FIELD_NONE;
			} else if (field == FIELD_BYTES &&
					ri4_append_byte(&bytes, &byte_count, &byte_space, value) != ERROR_OK) {
				LOG_ERROR("mchp_ri4: invalid script byte '%s'", value);
				free(name); free(processor); free(bytes);
				return ERROR_FAIL;
			}
		}
	}
	int result = ri4_add_script(session, name, processor, bytes, byte_count);
	free(name);
	free(processor);
	return result;
}

static char *ri4_xml_text(char *begin, char *end, const char *tag)
{
	char open[48];
	char close[48];
	snprintf(open, sizeof(open), "<%s>", tag);
	snprintf(close, sizeof(close), "</%s>", tag);
	char *start = strstr(begin, open);
	if (!start || start >= end)
		return NULL;
	start += strlen(open);
	char *stop = strstr(start, close);
	if (!stop || stop > end)
		return NULL;
	char saved = *stop;
	*stop = '\0';
	char *value = strdup(ri4_trim(start));
	*stop = saved;
	return value;
}

static int ri4_parse_xml(struct mchp_ri4_native *session, char *text)
{
	char *cursor = text;
	while ((cursor = strstr(cursor, "<script"))) {
		cursor = strchr(cursor, '>');
		if (!cursor)
			break;
		cursor++;
		char *end = strstr(cursor, "</script>");
		if (!end)
			return ERROR_FAIL;
		char *name = ri4_xml_text(cursor, end, "function");
		char *processor = ri4_xml_text(cursor, end, "processor");
		uint8_t *bytes = NULL;
		size_t used = 0;
		size_t allocated = 0;
		char *byte_cursor = cursor;
		while ((byte_cursor = strstr(byte_cursor, "<byte>")) && byte_cursor < end) {
			byte_cursor += 6;
			char *byte_end = strstr(byte_cursor, "</byte>");
			if (!byte_end || byte_end > end)
				break;
			char saved = *byte_end;
			*byte_end = '\0';
			int result = ri4_append_byte(&bytes, &used, &allocated, ri4_trim(byte_cursor));
			*byte_end = saved;
			if (result != ERROR_OK) {
				free(name); free(processor); free(bytes);
				return result;
			}
			byte_cursor = byte_end + 7;
		}
		int result = ri4_add_script(session, name, processor, bytes, used);
		free(name);
		free(processor);
		if (result != ERROR_OK)
			return result;
		cursor = end + 9;
	}
	return ERROR_OK;
}

static int ri4_load_scripts(struct mchp_ri4_native *session, const char *path)
{
	if (!path || !*path)
		return ERROR_OK;
	char *text = NULL;
	size_t length = 0;
	int result = ri4_read_catalog(path, &text, &length);
	if (result != ERROR_OK)
		return result;
	char *cursor = text;
	while (*cursor && isspace((unsigned char)*cursor))
		cursor++;
	result = *cursor == '<' ? ri4_parse_xml(session, text) : ri4_parse_yaml(session, text);
	free(text);
	if (result != ERROR_OK)
		LOG_ERROR("mchp_ri4: failed to parse script catalog '%s'", path);
	return result;
}

static struct ri4_script *ri4_find_script(struct mchp_ri4_native *session,
	const char *name)
{
	for (struct ri4_script *script = session->scripts; script; script = script->next) {
		if (strcasecmp(script->name, name) == 0)
			return script;
		if (session->suffix && *session->suffix) {
			size_t wanted = strlen(name);
			size_t suffix = strlen(session->suffix);
			if (strlen(script->name) == wanted + suffix &&
					strncasecmp(script->name, name, wanted) == 0 &&
					strcasecmp(script->name + wanted, session->suffix) == 0)
				return script;
		}
	}
	return NULL;
}

#ifdef HAVE_LIBUSB1
static int ri4_bulk(struct mchp_ri4_native *session, uint8_t endpoint,
	uint8_t *data, int length, unsigned int timeout, int *transferred)
{
	int result = libusb_bulk_transfer(session->usb, endpoint, data, length,
		transferred, timeout);
	if (result != LIBUSB_SUCCESS) {
		LOG_ERROR("mchp_ri4: USB endpoint 0x%02x failed: %s", endpoint,
			libusb_error_name(result));
		return ERROR_FAIL;
	}
	return ERROR_OK;
}

static int ri4_write_all(struct mchp_ri4_native *session, uint8_t endpoint,
	const uint8_t *data, size_t length, unsigned int timeout)
{
	while (length) {
		int count = 0;
		int chunk = (int)MIN(length, (size_t)INT_MAX);
		int result = ri4_bulk(session, endpoint, (uint8_t *)data, chunk, timeout, &count);
		if (result != ERROR_OK || count <= 0)
			return ERROR_FAIL;
		data += count;
		length -= (size_t)count;
	}
	return ERROR_OK;
}

static int ri4_read_some(struct mchp_ri4_native *session, uint8_t endpoint,
	uint8_t *data, size_t length, unsigned int timeout, size_t *actual)
{
	int count = 0;
	int result = ri4_bulk(session, endpoint, data,
		(int)MIN(length, (size_t)INT_MAX), timeout, &count);
	if (result != ERROR_OK)
		return result;
	*actual = (size_t)count;
	return ERROR_OK;
}

static int ri4_read_exact(struct mchp_ri4_native *session, uint8_t endpoint,
	uint8_t *data, size_t length, unsigned int timeout)
{
	while (length) {
		size_t count = 0;
		int result = ri4_read_some(session, endpoint, data, length, timeout, &count);
		if (result != ERROR_OK || count == 0)
			return ERROR_FAIL;
		data += count;
		length -= count;
	}
	return ERROR_OK;
}

static int ri4_side_command(struct mchp_ri4_native *session,
	const uint8_t *request, size_t request_length, uint8_t *reply, size_t *reply_length,
	unsigned int timeout)
{
	int result = ri4_write_all(session, RI4_SIDE_OUT, request, request_length, timeout);
	if (result != ERROR_OK)
		return result;
	return ri4_read_some(session, RI4_SIDE_IN, reply, RI4_REPLY_SIZE,
		timeout, reply_length);
}

static size_t ri4_make_header(uint8_t *buffer, uint32_t type,
	const uint8_t *payload, size_t payload_length, uint32_t transfer_length)
{
	ri4_put_u32(buffer, type);
	ri4_put_u32(buffer + 4, 0);
	ri4_put_u32(buffer + 8, RI4_HEADER_SIZE + payload_length);
	ri4_put_u32(buffer + 12, transfer_length);
	if (payload_length)
		memcpy(buffer + RI4_HEADER_SIZE, payload, payload_length);
	return RI4_HEADER_SIZE + payload_length;
}

static int ri4_check_reply(const uint8_t *reply, size_t length, bool ack)
{
	if (length < RI4_HEADER_SIZE || ri4_get_u32(reply) != RI4_RESULT)
		return ERROR_FAIL;
	uint32_t byte_count = ri4_get_u32(reply + 8);
	if (byte_count > length || byte_count < RI4_HEADER_SIZE)
		return ERROR_FAIL;
	if (byte_count == RI4_HEADER_SIZE)
		return ERROR_OK;
	if (byte_count < RI4_HEADER_SIZE + (ack ? 4U : 8U))
		return ERROR_FAIL;
	uint32_t status = ri4_get_u32(reply + RI4_HEADER_SIZE);
	if (status) {
		LOG_ERROR("mchp_ri4: RI4 script engine returned status 0x%08" PRIx32, status);
		return ERROR_FAIL;
	}
	return ERROR_OK;
}

static void ri4_recover(struct mchp_ri4_native *session, uint32_t flush)
{
	uint8_t request[RI4_HEADER_SIZE];
	uint8_t reply[RI4_REPLY_SIZE];
	size_t reply_length = 0;
	size_t length = ri4_make_header(request, RI4_ABORT_SCRIPTING_ENGINE, NULL, 0, 0);
	if (ri4_side_command(session, request, length, reply, &reply_length, RI4_FAST_TIMEOUT) != ERROR_OK) {
		uint8_t reset = RI4_NUCLEAR_RESET;
		(void)ri4_side_command(session, &reset, 1, reply, &reply_length, RI4_FAST_TIMEOUT);
		return;
	}
	if (flush) {
		length = ri4_make_header(request, flush, NULL, 0, 0);
		(void)ri4_side_command(session, request, length, reply, &reply_length, RI4_FAST_TIMEOUT);
	}
}

static int ri4_transfer(struct mchp_ri4_native *session, uint32_t type,
	const uint8_t *payload, size_t payload_length, uint8_t *data, size_t data_length)
{
	if (payload_length > UINT32_MAX - RI4_HEADER_SIZE || data_length > UINT32_MAX)
		return ERROR_FAIL;
	uint8_t *request = malloc(RI4_HEADER_SIZE + payload_length);
	uint8_t reply[RI4_REPLY_SIZE];
	if (!request)
		return ERROR_FAIL;
	size_t request_length = ri4_make_header(request, type, payload, payload_length,
		(uint32_t)data_length);
	size_t reply_length = 0;
	int result = ri4_side_command(session, request, request_length, reply,
		&reply_length, RI4_FAST_TIMEOUT);
	free(request);
	if (result != ERROR_OK) {
		ri4_recover(session, 0);
		return result;
	}
	result = ri4_check_reply(reply, reply_length, type != RI4_SCRIPT_NO_DATA);
	if (result != ERROR_OK) {
		ri4_recover(session, 0);
		return result;
	}
	if (type == RI4_SCRIPT_NO_DATA)
		return ERROR_OK;

	if (data_length) {
		if (type == RI4_SCRIPT_UPLOAD)
			result = ri4_read_exact(session, RI4_DATA_IN, data, data_length, RI4_DATA_TIMEOUT);
		else
			result = ri4_write_all(session, RI4_DATA_OUT, data, data_length, RI4_DATA_TIMEOUT);
		if (result != ERROR_OK) {
			ri4_recover(session, type == RI4_SCRIPT_UPLOAD ? RI4_FLUSH_UPLOAD : RI4_FLUSH_DOWNLOAD);
			return result;
		}
	}

	uint8_t done[RI4_HEADER_SIZE];
	ri4_make_header(done, RI4_SCRIPT_DONE, NULL, 0, 0);
	result = ri4_side_command(session, done, sizeof(done), reply, &reply_length, RI4_FAST_TIMEOUT);
	if (result == ERROR_OK)
		result = ri4_check_reply(reply, reply_length, false);
	if (result != ERROR_OK)
		ri4_recover(session, 0);
	return result;
}
#endif

static int ri4_run(struct mchp_ri4_native *session, const char *name,
	const uint32_t *params, size_t param_count, uint8_t *data, size_t data_length,
	uint32_t transfer_type)
{
	struct ri4_script *script = ri4_find_script(session, name);
	if (!script)
		return ERROR_TARGET_RESOURCE_NOT_AVAILABLE;
	if (param_count > (SIZE_MAX - 8U - script->length) / 4U)
		return ERROR_FAIL;
	size_t payload_length = 8U + param_count * 4U + script->length;
	uint8_t *payload = malloc(payload_length);
	if (!payload)
		return ERROR_FAIL;
	ri4_put_u32(payload, (uint32_t)(param_count * 4U));
	ri4_put_u32(payload + 4, (uint32_t)script->length);
	for (size_t i = 0; i < param_count; i++)
		ri4_put_u32(payload + 8U + i * 4U, params[i]);
	memcpy(payload + 8U + param_count * 4U, script->data, script->length);
#ifdef HAVE_LIBUSB1
	int result = ri4_transfer(session, transfer_type, payload, payload_length, data, data_length);
#else
	int result = ERROR_FAIL;
#endif
	free(payload);
	return result;
}

static int ri4_run_first(struct mchp_ri4_native *session, const char *const *names,
	size_t name_count, const uint32_t *params, size_t param_count,
	uint8_t *data, size_t data_length, uint32_t transfer_type)
{
	for (size_t i = 0; i < name_count; i++) {
		if (!ri4_find_script(session, names[i]))
			continue;
		return ri4_run(session, names[i], params, param_count, data, data_length, transfer_type);
	}
	LOG_ERROR("mchp_ri4: no suitable RI4 script is available for this operation");
	return ERROR_TARGET_RESOURCE_NOT_AVAILABLE;
}

static bool ri4_has_any(struct mchp_ri4_native *session,
	const char *const *names, size_t count)
{
	for (size_t i = 0; i < count; i++)
		if (ri4_find_script(session, names[i]))
			return true;
	return false;
}

static int ri4_enter_programming(struct mchp_ri4_native *session)
{
	static const char *const enter[] = {"EnterTMOD_LV", "EnterTMOD_HV",
		"EnterTMOD_PE", "EnterProgMode"};
	if (!ri4_has_any(session, enter, ARRAY_SIZE(enter)))
		return ERROR_OK;
	if (ri4_find_script(session, "SetSpeedFromDevice")) {
		int result = ri4_run(session, "SetSpeedFromDevice", NULL, 0,
			NULL, 0, RI4_SCRIPT_NO_DATA);
		if (result != ERROR_OK)
			return result;
	}
	return ri4_run_first(session, enter, ARRAY_SIZE(enter), NULL, 0,
		NULL, 0, RI4_SCRIPT_NO_DATA);
}

static int ri4_exit_programming(struct mchp_ri4_native *session)
{
	static const char *const exit[] = {"ExitTMOD", "ExitProgMode"};
	if (!ri4_has_any(session, exit, ARRAY_SIZE(exit)))
		return ERROR_OK;
	return ri4_run_first(session, exit, ARRAY_SIZE(exit), NULL, 0,
		NULL, 0, RI4_SCRIPT_NO_DATA);
}

static int ri4_open_usb(struct mchp_ri4_native *session,
	const struct mchp_ri4_native_config *config)
{
#ifdef HAVE_LIBUSB1
	int result = libusb_init(&session->usb_context);
	if (result != LIBUSB_SUCCESS)
		return ERROR_FAIL;
	libusb_device **devices = NULL;
	ssize_t count = libusb_get_device_list(session->usb_context, &devices);
	if (count < 0)
		return ERROR_FAIL;
	for (ssize_t i = 0; i < count; i++) {
		struct libusb_device_descriptor descriptor;
		if (libusb_get_device_descriptor(devices[i], &descriptor) != LIBUSB_SUCCESS ||
				descriptor.idVendor != config->vid || descriptor.idProduct != config->pid)
			continue;
		libusb_device_handle *candidate = NULL;
		if (libusb_open(devices[i], &candidate) != LIBUSB_SUCCESS)
			continue;
		if (config->serial && *config->serial) {
			unsigned char serial[256];
			int serial_len = descriptor.iSerialNumber ?
				libusb_get_string_descriptor_ascii(candidate, descriptor.iSerialNumber,
					serial, sizeof(serial) - 1U) : -1;
			if (serial_len < 0) {
				libusb_close(candidate);
				continue;
			}
			serial[serial_len] = '\0';
			if (strcmp((char *)serial, config->serial) != 0) {
				libusb_close(candidate);
				continue;
			}
		}
		session->usb = candidate;
		break;
	}
	libusb_free_device_list(devices, 1);
	if (!session->usb) {
		LOG_ERROR("mchp_ri4: no USB probe found for %04x:%04x%s%s",
			config->vid, config->pid, config->serial && *config->serial ? " serial " : "",
			config->serial && *config->serial ? config->serial : "");
		return ERROR_FAIL;
	}
	(void)libusb_set_auto_detach_kernel_driver(session->usb, 1);
	result = libusb_claim_interface(session->usb, RI4_INTERFACE);
	if (result != LIBUSB_SUCCESS) {
		LOG_ERROR("mchp_ri4: cannot claim USB interface 0: %s", libusb_error_name(result));
		return ERROR_FAIL;
	}
	return ERROR_OK;
#else
	(void)session;
	(void)config;
	LOG_ERROR("mchp_ri4: OpenOCD was built without libusb-1.0 support");
	return ERROR_FAIL;
#endif
}

int mchp_ri4_native_open(struct mchp_ri4_native **session_out,
	const struct mchp_ri4_native_config *config)
{
	if (!session_out || !config || !config->processor || !*config->processor ||
			!config->scripts_path || !*config->scripts_path)
		return ERROR_COMMAND_ARGUMENT_INVALID;
	struct mchp_ri4_native *session = calloc(1, sizeof(*session));
	if (!session)
		return ERROR_FAIL;
	session->processor = strdup(config->processor);
	session->family = strdup(config->family ? config->family : "");
	session->suffix = strdup(config->script_suffix ? config->script_suffix : "");
	if (!session->processor || !session->family || !session->suffix) {
		mchp_ri4_native_close(session);
		return ERROR_FAIL;
	}
	int result = ri4_load_scripts(session, config->scripts_path);
	if (result == ERROR_OK)
		result = ri4_load_scripts(session, config->tool_scripts_path);
	if (result != ERROR_OK) {
		mchp_ri4_native_close(session);
		return result;
	}
	if (!session->scripts) {
		LOG_ERROR("mchp_ri4: catalog has no scripts for processor '%s'", config->processor);
		mchp_ri4_native_close(session);
		return ERROR_FAIL;
	}
	result = ri4_open_usb(session, config);
	if (result != ERROR_OK) {
		mchp_ri4_native_close(session);
		return result;
	}
	LOG_INFO("mchp_ri4: native USB session opened for %s (%04x:%04x)",
		config->processor, config->vid, config->pid);
	*session_out = session;
	return ERROR_OK;
}

void mchp_ri4_native_close(struct mchp_ri4_native *session)
{
	if (!session)
		return;
#ifdef HAVE_LIBUSB1
	if (session->usb) {
		libusb_release_interface(session->usb, RI4_INTERFACE);
		libusb_close(session->usb);
	}
	if (session->usb_context)
		libusb_exit(session->usb_context);
#endif
	while (session->scripts) {
		struct ri4_script *next = session->scripts->next;
		free(session->scripts->name);
		free(session->scripts->data);
		free(session->scripts);
		session->scripts = next;
	}
	free(session->processor);
	free(session->family);
	free(session->suffix);
	free(session);
}

void mchp_ri4_native_get_caps(struct mchp_ri4_native *session,
	struct mchp_ri4_native_caps *caps)
{
	static const char *const erase[] = {"EraseChip", "EraseProgmemRange"};
	static const char *const reads[] = {"ReadProgmemPE", "ReadProgmem", "ReadProgmemDE", "ReadRAM"};
	static const char *const writes[] = {"WriteProgmemPE", "WriteProgmem", "WriteProgmemDE", "WriteRAM"};
	memset(caps, 0, sizeof(*caps));
	caps->erase = ri4_has_any(session, erase, ARRAY_SIZE(erase));
	caps->debug = ri4_find_script(session, "EnterDebugMode") &&
		ri4_find_script(session, "Halt") && ri4_find_script(session, "Run") &&
		ri4_find_script(session, "GetPC");
	caps->poll = caps->debug;
	caps->set_pc = ri4_find_script(session, "SetPC") != NULL;
	caps->breakpoints = ri4_find_script(session, "SetHWBP") && ri4_find_script(session, "ClearHWBP");
	caps->watchpoints = ri4_find_script(session, "SetDataHWBP") && ri4_find_script(session, "ClearHWBP");
	caps->memory_read = ri4_has_any(session, reads, ARRAY_SIZE(reads));
	caps->memory_write = ri4_has_any(session, writes, ARRAY_SIZE(writes));
}

int mchp_ri4_native_enter_debug(struct mchp_ri4_native *session)
{
	static const char *const names[] = {"EnterDebugMode", "EnterDebugModeHvSp",
		"EnterDebugModeHvSpRst", "EnterDebugModeHvUpt"};
	return ri4_run_first(session, names, ARRAY_SIZE(names), NULL, 0, NULL, 0, RI4_SCRIPT_NO_DATA);
}

int mchp_ri4_native_halt(struct mchp_ri4_native *session)
{
	return ri4_run(session, "Halt", NULL, 0, NULL, 0, RI4_SCRIPT_NO_DATA);
}

int mchp_ri4_native_run(struct mchp_ri4_native *session)
{
	return ri4_run(session, "Run", NULL, 0, NULL, 0, RI4_SCRIPT_NO_DATA);
}

int mchp_ri4_native_step(struct mchp_ri4_native *session)
{
	static const char *const names[] = {"SingleStep", "SingleStepUFEX"};
	return ri4_run_first(session, names, ARRAY_SIZE(names), NULL, 0, NULL, 0, RI4_SCRIPT_NO_DATA);
}

int mchp_ri4_native_reset(struct mchp_ri4_native *session)
{
	static const char *const names[] = {"Reset", "ResetToRun", "MCLRReset", "Run"};
	return ri4_run_first(session, names, ARRAY_SIZE(names), NULL, 0, NULL, 0, RI4_SCRIPT_NO_DATA);
}

int mchp_ri4_native_is_halted(struct mchp_ri4_native *session, bool *halted)
{
#ifdef HAVE_LIBUSB1
	static const char key[] = "Target Halted";
	uint8_t request[RI4_HEADER_SIZE + sizeof(key)];
	uint8_t reply[RI4_REPLY_SIZE];
	size_t request_length = ri4_make_header(request, RI4_GET_STATUS_FROM_KEY,
		(const uint8_t *)key, sizeof(key), 0);
	size_t reply_length = 0;
	int result = ri4_side_command(session, request, request_length, reply,
		&reply_length, RI4_FAST_TIMEOUT);
	if (result != ERROR_OK || reply_length <= RI4_HEADER_SIZE)
		return ERROR_FAIL;
	const char *value = (const char *)reply + RI4_HEADER_SIZE;
	size_t value_space = reply_length - RI4_HEADER_SIZE;
	if (!memchr(value, '\0', value_space))
		return ERROR_FAIL;
	if (strcasecmp(value, "1") == 0 || strcasecmp(value, "true") == 0 ||
			strcasecmp(value, "yes") == 0 || strcasecmp(value, "halted") == 0 ||
			strcasecmp(value, "stopped") == 0)
		*halted = true;
	else if (strcasecmp(value, "0") == 0 || strcasecmp(value, "false") == 0 ||
			strcasecmp(value, "no") == 0 || strcasecmp(value, "running") == 0)
		*halted = false;
	else
		return ERROR_FAIL;
	return ERROR_OK;
#else
	(void)session;
	(void)halted;
	return ERROR_FAIL;
#endif
}

int mchp_ri4_native_get_pc(struct mchp_ri4_native *session,
	unsigned int pc_bytes, uint32_t *pc)
{
	uint8_t data[4] = {0};
	uint32_t params[] = {0, pc_bytes};
	int result = ri4_run(session, "GetPC", params, ARRAY_SIZE(params), data,
		pc_bytes, RI4_SCRIPT_UPLOAD);
	if (result != ERROR_OK)
		result = ri4_run(session, "GetPC", NULL, 0, data, pc_bytes, RI4_SCRIPT_UPLOAD);
	if (result == ERROR_OK)
		*pc = ri4_get_u32(data);
	return result;
}

int mchp_ri4_native_set_pc(struct mchp_ri4_native *session, uint32_t pc)
{
	return ri4_run(session, "SetPC", &pc, 1, NULL, 0, RI4_SCRIPT_NO_DATA);
}

int mchp_ri4_native_read(struct mchp_ri4_native *session,
	uint32_t address, uint8_t *data, uint32_t length)
{
	static const char *const names[] = {"ReadProgmemPE", "ReadProgmem", "ReadProgmemDE", "ReadRAM"};
	uint32_t params[] = {address, length};
	int result = ri4_enter_programming(session);
	if (result == ERROR_OK)
		result = ri4_run_first(session, names, ARRAY_SIZE(names), params, ARRAY_SIZE(params),
		data, length, RI4_SCRIPT_UPLOAD);
	int exit_result = ri4_exit_programming(session);
	return result == ERROR_OK ? exit_result : result;
}

int mchp_ri4_native_write(struct mchp_ri4_native *session,
	uint32_t address, const uint8_t *data, uint32_t length)
{
	static const char *const names[] = {"WriteProgmemPE", "WriteProgmem", "WriteProgmemDE", "WriteRAM"};
	uint32_t params[] = {address, length};
	int result = ri4_enter_programming(session);
	if (result == ERROR_OK)
		result = ri4_run_first(session, names, ARRAY_SIZE(names), params, ARRAY_SIZE(params),
		(uint8_t *)data, length, RI4_SCRIPT_DOWNLOAD);
	int exit_result = ri4_exit_programming(session);
	return result == ERROR_OK ? exit_result : result;
}

int mchp_ri4_native_erase(struct mchp_ri4_native *session, unsigned int mode)
{
	static const char *const erase[] = {"EraseChip", "EraseProgmemRange"};
	int result = ri4_enter_programming(session);
	if (result != ERROR_OK)
		return result;
	uint32_t value = mode;
	result = ri4_run_first(session, erase, ARRAY_SIZE(erase),
		mode ? &value : NULL, mode ? 1 : 0, NULL, 0, RI4_SCRIPT_NO_DATA);
	int exit_result = ri4_exit_programming(session);
	return result == ERROR_OK ? exit_result : result;
}

int mchp_ri4_native_set_breakpoint(struct mchp_ri4_native *session,
	unsigned int slot, uint32_t address)
{
	uint32_t params[] = {slot, address};
	return ri4_run(session, "SetHWBP", params, ARRAY_SIZE(params), NULL, 0, RI4_SCRIPT_NO_DATA);
}

int mchp_ri4_native_set_watchpoint(struct mchp_ri4_native *session,
	unsigned int access, unsigned int slot, uint32_t address)
{
	uint32_t params[] = {access, slot, address};
	return ri4_run(session, "SetDataHWBP", params, ARRAY_SIZE(params), NULL, 0, RI4_SCRIPT_NO_DATA);
}

int mchp_ri4_native_clear_point(struct mchp_ri4_native *session,
	unsigned int slot)
{
	uint32_t value = slot;
	return ri4_run(session, "ClearHWBP", &value, 1, NULL, 0, RI4_SCRIPT_NO_DATA);
}
