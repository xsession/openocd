// SPDX-License-Identifier: GPL-2.0-or-later
/*
 * Microchip RI4 bridge target for OpenOCD.
 *
 * The USB protocol and device-script knowledge stay in the companion Python
 * bridge.  This target driver only translates OpenOCD target operations to
 * newline-delimited JSON requests.  It intentionally fails unsupported
 * features instead of mutating OpenOCD state without touching the target.
 */
#ifdef HAVE_CONFIG_H
#include "config.h"
#endif

#include "target.h"
#include "target_type.h"
#include "register.h"
#include "breakpoints.h"
#include "mchp_ri4_bridge.h"

#include <helper/binarybuffer.h>
#include <helper/command.h>
#include <helper/log.h>
#include <helper/replacements.h>

#include <errno.h>
#include <inttypes.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifdef HAVE_SYS_SOCKET_H
#include <sys/socket.h>
#endif
#ifdef HAVE_NETDB_H
#include <netdb.h>
#endif

#define MCHP_RI4_TARGET_NAME "mchp_ri4_bridge"
#define MCHP_RI4_DEFAULT_HOST "127.0.0.1"
#define MCHP_RI4_DEFAULT_PORT 9123
#define MCHP_RI4_RESPONSE_LIMIT (1024U * 1024U)
#define MCHP_RI4_TIMEOUT_MS 30000U

struct mchp_ri4_capabilities {
	bool flash;
	bool erase;
	bool verify;
	bool debug;
	bool poll;
	bool set_pc;
	bool breakpoints;
	bool watchpoints;
	bool memory_read;
	bool memory_write;
};

struct mchp_ri4_bridge {
	char *host;
	unsigned int port;
	char *tool;
	uint16_t vid;
	uint16_t pid;
	char *family;
	char *processor;
	char *scripts_path;
	char *tool_scripts_path;
	char *script_suffix;
	char *serial_number;
	unsigned int pc_bytes;
	int sock;
	bool session_started;
	struct mchp_ri4_capabilities caps;

	struct reg_cache *core_cache;
	struct reg *pc_reg;
	uint8_t *pc_value;
};

struct mchp_ri4_reg {
	struct target *target;
};

static struct reg_feature mchp_ri4_reg_feature = {
	.name = "org.gnu.gdb.mchp-ri4.core",
};

static int mchp_ri4_request(struct mchp_ri4_bridge *bridge,
		const char *command, const char *args_json, char **response_out);
static int mchp_ri4_get_pc_value(struct target *target, uint32_t *pc);
static int mchp_ri4_set_pc_value(struct target *target, uint32_t pc);

bool mchp_ri4_bridge_is_target(const struct target *target)
{
	/* OpenOCD copies struct target_type per target, so pointer identity with
	 * mchp_ri4_bridge_target is not stable.  Match the registered type name. */
	return target && target->type && target->type->name &&
		strcmp(target->type->name, MCHP_RI4_TARGET_NAME) == 0;
}

static struct mchp_ri4_bridge *target_to_mchp_ri4(struct target *target)
{
	return target->arch_info;
}

static void mchp_ri4_replace_string(char **destination, const char *value)
{
	free(*destination);
	*destination = value ? strdup(value) : NULL;
}

static int mchp_ri4_parse_u32(const char *text, uint32_t *value)
{
	char *end = NULL;
	errno = 0;
	unsigned long parsed = strtoul(text, &end, 0);
	if (errno || !end || *end != '\0' || parsed > UINT32_MAX)
		return ERROR_COMMAND_ARGUMENT_INVALID;
	*value = (uint32_t)parsed;
	return ERROR_OK;
}

static char *mchp_ri4_json_escape(const char *input)
{
	if (!input)
		input = "";
	size_t length = strlen(input);
	if (length > (SIZE_MAX - 1U) / 6U)
		return NULL;
	char *output = malloc(length * 6U + 1U);
	if (!output)
		return NULL;

	char *cursor = output;
	for (const unsigned char *source = (const unsigned char *)input; *source; source++) {
		switch (*source) {
		case '"':
			*cursor++ = '\\';
			*cursor++ = '"';
			break;
		case '\\':
			*cursor++ = '\\';
			*cursor++ = '\\';
			break;
		case '\b':
			*cursor++ = '\\';
			*cursor++ = 'b';
			break;
		case '\f':
			*cursor++ = '\\';
			*cursor++ = 'f';
			break;
		case '\n':
			*cursor++ = '\\';
			*cursor++ = 'n';
			break;
		case '\r':
			*cursor++ = '\\';
			*cursor++ = 'r';
			break;
		case '\t':
			*cursor++ = '\\';
			*cursor++ = 't';
			break;
		default:
			if (*source < 0x20) {
				snprintf(cursor, 7, "\\u%04x", *source);
				cursor += 6;
			} else {
				*cursor++ = (char)*source;
			}
			break;
		}
	}
	*cursor = '\0';
	return output;
}

static const char *mchp_ri4_json_value(const char *json, const char *key)
{
	char pattern[96];
	int written = snprintf(pattern, sizeof(pattern), "\"%s\":", key);
	if (written < 0 || (size_t)written >= sizeof(pattern))
		return NULL;
	const char *found = strstr(json, pattern);
	return found ? found + written : NULL;
}

static bool mchp_ri4_json_bool(const char *json, const char *key, bool default_value)
{
	const char *value = mchp_ri4_json_value(json, key);
	if (!value)
		return default_value;
	if (strncmp(value, "true", 4) == 0)
		return true;
	if (strncmp(value, "false", 5) == 0)
		return false;
	return default_value;
}

static int mchp_ri4_json_u32(const char *json, const char *key, uint32_t *result)
{
	const char *value = mchp_ri4_json_value(json, key);
	if (!value)
		return ERROR_FAIL;
	char *end = NULL;
	errno = 0;
	unsigned long parsed = strtoul(value, &end, 0);
	if (errno || end == value || parsed > UINT32_MAX)
		return ERROR_FAIL;
	*result = (uint32_t)parsed;
	return ERROR_OK;
}

static int mchp_ri4_json_string(const char *json, const char *key,
		char *output, size_t output_size)
{
	const char *value = mchp_ri4_json_value(json, key);
	if (!value || *value != '"' || output_size == 0)
		return ERROR_FAIL;
	value++;
	size_t used = 0;
	while (*value && *value != '"') {
		if (used + 1 >= output_size)
			return ERROR_FAIL;
		if (*value == '\\') {
			value++;
			if (!*value)
				return ERROR_FAIL;
			switch (*value) {
			case '"': output[used++] = '"'; break;
			case '\\': output[used++] = '\\'; break;
			case 'n': output[used++] = '\n'; break;
			case 'r': output[used++] = '\r'; break;
			case 't': output[used++] = '\t'; break;
			default: output[used++] = *value; break;
			}
			value++;
			continue;
		}
		output[used++] = *value++;
	}
	if (*value != '"')
		return ERROR_FAIL;
	output[used] = '\0';
	return ERROR_OK;
}

static int mchp_ri4_send_all(int sock, const char *data, size_t length)
{
	while (length > 0) {
		int sent = write_socket(sock, data, (unsigned int)MIN(length, (size_t)INT_MAX));
		if (sent <= 0)
			return ERROR_FAIL;
		data += sent;
		length -= (size_t)sent;
	}
	return ERROR_OK;
}

static int mchp_ri4_connect(struct mchp_ri4_bridge *bridge)
{
	if (bridge->sock >= 0)
		return ERROR_OK;

	char service[16];
	snprintf(service, sizeof(service), "%u", bridge->port);
	struct addrinfo hints;
	memset(&hints, 0, sizeof(hints));
	hints.ai_family = AF_UNSPEC;
	hints.ai_socktype = SOCK_STREAM;

	struct addrinfo *addresses = NULL;
	int gai_result = getaddrinfo(bridge->host, service, &hints, &addresses);
	if (gai_result != 0) {
		LOG_ERROR("mchp_ri4: cannot resolve bridge host '%s': %s",
			bridge->host, gai_strerror(gai_result));
		return ERROR_FAIL;
	}

	for (struct addrinfo *address = addresses; address; address = address->ai_next) {
		int sock = (int)socket(address->ai_family, address->ai_socktype, address->ai_protocol);
		if (sock < 0)
			continue;
		if (connect(sock, address->ai_addr, address->ai_addrlen) == 0) {
			bridge->sock = sock;
			socket_recv_timeout(sock, MCHP_RI4_TIMEOUT_MS);
			break;
		}
		close_socket(sock);
	}
	freeaddrinfo(addresses);

	if (bridge->sock < 0) {
		LOG_ERROR("mchp_ri4: cannot connect to bridge at %s:%u", bridge->host, bridge->port);
		return ERROR_FAIL;
	}
	return ERROR_OK;
}

static void mchp_ri4_disconnect(struct mchp_ri4_bridge *bridge)
{
	if (bridge->sock >= 0) {
		close_socket(bridge->sock);
		bridge->sock = -1;
	}
}

static int mchp_ri4_receive_line(struct mchp_ri4_bridge *bridge, char **response_out)
{
	char *response = malloc(MCHP_RI4_RESPONSE_LIMIT + 1U);
	if (!response)
		return ERROR_FAIL;

	size_t used = 0;
	while (used < MCHP_RI4_RESPONSE_LIMIT) {
		char byte = 0;
		int received = read_socket(bridge->sock, &byte, 1);
		if (received <= 0) {
			free(response);
			mchp_ri4_disconnect(bridge);
			return ERROR_FAIL;
		}
		if (byte == '\n') {
			response[used] = '\0';
			*response_out = response;
			return ERROR_OK;
		}
		response[used++] = byte;
	}
	free(response);
	LOG_ERROR("mchp_ri4: bridge response exceeds 1 MiB");
	return ERROR_FAIL;
}

static int mchp_ri4_request(struct mchp_ri4_bridge *bridge,
		const char *command, const char *args_json, char **response_out)
{
	int result = mchp_ri4_connect(bridge);
	if (result != ERROR_OK)
		return result;

	if (!args_json)
		args_json = "{}";
	size_t request_size = strlen(command) + strlen(args_json) + 40U;
	char *request = malloc(request_size);
	if (!request)
		return ERROR_FAIL;
	snprintf(request, request_size, "{\"command\":\"%s\",\"args\":%s}\n",
		command, args_json);

	result = mchp_ri4_send_all(bridge->sock, request, strlen(request));
	free(request);
	if (result != ERROR_OK) {
		mchp_ri4_disconnect(bridge);
		return result;
	}

	char *response = NULL;
	result = mchp_ri4_receive_line(bridge, &response);
	if (result != ERROR_OK)
		return result;
	if (!strstr(response, "\"ok\":true")) {
		char message[256] = "bridge operation failed";
		(void)mchp_ri4_json_string(response, "message", message, sizeof(message));
		LOG_ERROR("mchp_ri4: %s: %s", command, message);
		free(response);
		return ERROR_FAIL;
	}
	*response_out = response;
	return ERROR_OK;
}

static int mchp_ri4_start_session(struct mchp_ri4_bridge *bridge)
{
	if (bridge->session_started)
		return ERROR_OK;
	if (!bridge->processor || !*bridge->processor || !bridge->scripts_path || !*bridge->scripts_path) {
		LOG_ERROR("mchp_ri4: processor and scripts path must be configured before init");
		return ERROR_FAIL;
	}

	char *tool = mchp_ri4_json_escape(bridge->tool);
	char *family = mchp_ri4_json_escape(bridge->family);
	char *processor = mchp_ri4_json_escape(bridge->processor);
	char *scripts = mchp_ri4_json_escape(bridge->scripts_path);
	char *tool_scripts = mchp_ri4_json_escape(bridge->tool_scripts_path);
	char *suffix = mchp_ri4_json_escape(bridge->script_suffix);
	char *serial = mchp_ri4_json_escape(bridge->serial_number);
	if (!tool || !family || !processor || !scripts || !tool_scripts || !suffix || !serial) {
		free(tool); free(family); free(processor); free(scripts);
		free(tool_scripts); free(suffix); free(serial);
		return ERROR_FAIL;
	}

	size_t args_size = strlen(tool) + strlen(family) + strlen(processor) + strlen(scripts) +
		strlen(tool_scripts) + strlen(suffix) + strlen(serial) + 320U;
	char *args = malloc(args_size);
	if (!args) {
		free(tool); free(family); free(processor); free(scripts);
		free(tool_scripts); free(suffix); free(serial);
		return ERROR_FAIL;
	}
	snprintf(args, args_size,
		"{\"tool\":\"%s\",\"vid\":%u,\"pid\":%u,\"family\":\"%s\","
		"\"processor\":\"%s\",\"scriptsPath\":\"%s\",\"toolScriptsPath\":\"%s\","
		"\"scriptSuffix\":\"%s\",\"serialNumber\":\"%s\",\"pcBytes\":%u,"
		"\"resetDevice\":false}",
		tool, bridge->vid, bridge->pid, family, processor, scripts, tool_scripts,
		suffix, serial, bridge->pc_bytes);
	free(tool); free(family); free(processor); free(scripts);
	free(tool_scripts); free(suffix); free(serial);

	char *response = NULL;
	int result = mchp_ri4_request(bridge, "startSession", args, &response);
	free(args);
	free(response);
	if (result == ERROR_OK)
		bridge->session_started = true;
	return result;
}

static void mchp_ri4_end_session(struct mchp_ri4_bridge *bridge)
{
	if (bridge->session_started && bridge->sock >= 0) {
		char *response = NULL;
		(void)mchp_ri4_request(bridge, "endSession", "{}", &response);
		free(response);
	}
	bridge->session_started = false;
	mchp_ri4_disconnect(bridge);
}

static int mchp_ri4_refresh_capabilities(struct mchp_ri4_bridge *bridge)
{
	char *response = NULL;
	int result = mchp_ri4_request(bridge, "capabilities", "{}", &response);
	if (result != ERROR_OK)
		return result;
	bridge->caps.flash = mchp_ri4_json_bool(response, "flash", false);
	bridge->caps.erase = mchp_ri4_json_bool(response, "erase", false);
	bridge->caps.verify = mchp_ri4_json_bool(response, "verify", false);
	bridge->caps.debug = mchp_ri4_json_bool(response, "debug", false);
	bridge->caps.poll = mchp_ri4_json_bool(response, "poll", false);
	bridge->caps.set_pc = mchp_ri4_json_bool(response, "setPc", false);
	bridge->caps.breakpoints = mchp_ri4_json_bool(response, "breakpoints", false);
	bridge->caps.watchpoints = mchp_ri4_json_bool(response, "watchpoints", false);
	bridge->caps.memory_read = mchp_ri4_json_bool(response, "memoryRead", false);
	bridge->caps.memory_write = mchp_ri4_json_bool(response, "memoryWrite", false);
	free(response);
	return ERROR_OK;
}

static int mchp_ri4_simple_request(struct target *target, const char *command)
{
	struct mchp_ri4_bridge *bridge = target_to_mchp_ri4(target);
	char *response = NULL;
	int result = mchp_ri4_request(bridge, command, "{}", &response);
	free(response);
	return result;
}

static int mchp_ri4_poll(struct target *target)
{
	struct mchp_ri4_bridge *bridge = target_to_mchp_ri4(target);
	if (!bridge->caps.poll)
		return ERROR_TARGET_RESOURCE_NOT_AVAILABLE;

	char *response = NULL;
	int result = mchp_ri4_request(bridge, "targetStatus",
		"{\"refresh\":true,\"includePc\":false}", &response);
	if (result != ERROR_OK)
		return result;

	char state[24];
	result = mchp_ri4_json_string(response, "state", state, sizeof(state));
	free(response);
	if (result != ERROR_OK)
		return result;

	enum target_state previous = target->state;
	if (strcmp(state, "halted") == 0)
		target->state = TARGET_HALTED;
	else if (strcmp(state, "running") == 0)
		target->state = TARGET_RUNNING;
	else
		target->state = TARGET_UNKNOWN;

	if (previous != target->state) {
		if (target->state == TARGET_HALTED) {
			if (target->debug_reason == DBG_REASON_NOTHALTED)
				target->debug_reason = DBG_REASON_UNDEFINED;
			register_cache_invalidate(target->reg_cache);
			target_call_event_callbacks(target, TARGET_EVENT_HALTED);
		} else if (target->state == TARGET_RUNNING) {
			target_call_event_callbacks(target, TARGET_EVENT_RESUMED);
		}
	}
	return ERROR_OK;
}

static int mchp_ri4_halt(struct target *target)
{
	if (target->state == TARGET_HALTED)
		return ERROR_OK;
	int result = mchp_ri4_simple_request(target, "halt");
	if (result != ERROR_OK)
		return result;
	target->state = TARGET_HALTED;
	target->debug_reason = DBG_REASON_DBGRQ;
	register_cache_invalidate(target->reg_cache);
	target_call_event_callbacks(target, TARGET_EVENT_HALTED);
	return ERROR_OK;
}

static int mchp_ri4_resume(struct target *target, bool current,
		target_addr_t address, bool handle_breakpoints, bool debug_execution)
{
	(void)handle_breakpoints;
	(void)debug_execution;
	struct mchp_ri4_bridge *bridge = target_to_mchp_ri4(target);
	if (!current) {
		if (!bridge->caps.set_pc || address > UINT32_MAX)
			return ERROR_TARGET_RESOURCE_NOT_AVAILABLE;
		int result = mchp_ri4_set_pc_value(target, (uint32_t)address);
		if (result != ERROR_OK)
			return result;
	}
	int result = mchp_ri4_simple_request(target, "run");
	if (result != ERROR_OK)
		return result;
	target->state = TARGET_RUNNING;
	target->debug_reason = DBG_REASON_NOTHALTED;
	register_cache_invalidate(target->reg_cache);
	target_call_event_callbacks(target, TARGET_EVENT_RESUMED);
	return ERROR_OK;
}

static int mchp_ri4_step(struct target *target, bool current,
		target_addr_t address, bool handle_breakpoints)
{
	(void)handle_breakpoints;
	struct mchp_ri4_bridge *bridge = target_to_mchp_ri4(target);
	if (!current) {
		if (!bridge->caps.set_pc || address > UINT32_MAX)
			return ERROR_TARGET_RESOURCE_NOT_AVAILABLE;
		int result = mchp_ri4_set_pc_value(target, (uint32_t)address);
		if (result != ERROR_OK)
			return result;
	}
	int result = mchp_ri4_simple_request(target, "step");
	if (result != ERROR_OK)
		return result;
	target->state = TARGET_HALTED;
	target->debug_reason = DBG_REASON_SINGLESTEP;
	register_cache_invalidate(target->reg_cache);
	(void)mchp_ri4_get_pc_value(target, NULL);
	target_call_event_callbacks(target, TARGET_EVENT_HALTED);
	return ERROR_OK;
}

static int mchp_ri4_assert_reset(struct target *target)
{
	int result = mchp_ri4_simple_request(target, "reset");
	if (result != ERROR_OK)
		return result;
	target->state = TARGET_RESET;
	register_cache_invalidate(target->reg_cache);
	return ERROR_OK;
}

static int mchp_ri4_deassert_reset(struct target *target)
{
	if (target->reset_halt)
		return mchp_ri4_halt(target);
	return mchp_ri4_resume(target, true, 0, false, false);
}

static int mchp_ri4_soft_reset_halt(struct target *target)
{
	int result = mchp_ri4_assert_reset(target);
	if (result != ERROR_OK)
		return result;
	return mchp_ri4_halt(target);
}

static int mchp_ri4_get_pc_value(struct target *target, uint32_t *pc_out)
{
	struct mchp_ri4_bridge *bridge = target_to_mchp_ri4(target);
	char *response = NULL;
	int result = mchp_ri4_request(bridge, "getPc", "{}", &response);
	if (result != ERROR_OK)
		return result;
	uint32_t pc = 0;
	result = mchp_ri4_json_u32(response, "pc", &pc);
	free(response);
	if (result != ERROR_OK)
		return result;
	buf_set_u32(bridge->pc_value, 0, bridge->pc_reg->size, pc);
	bridge->pc_reg->valid = true;
	bridge->pc_reg->dirty = false;
	if (pc_out)
		*pc_out = pc;
	return ERROR_OK;
}

static int mchp_ri4_set_pc_value(struct target *target, uint32_t pc)
{
	struct mchp_ri4_bridge *bridge = target_to_mchp_ri4(target);
	char args[64];
	snprintf(args, sizeof(args), "{\"address\":%" PRIu32 "}", pc);
	char *response = NULL;
	int result = mchp_ri4_request(bridge, "setPc", args, &response);
	free(response);
	if (result != ERROR_OK)
		return result;
	buf_set_u32(bridge->pc_value, 0, bridge->pc_reg->size, pc);
	bridge->pc_reg->valid = true;
	bridge->pc_reg->dirty = false;
	return ERROR_OK;
}

static int mchp_ri4_reg_get(struct reg *reg)
{
	struct mchp_ri4_reg *arch_reg = reg->arch_info;
	if (arch_reg->target->state != TARGET_HALTED)
		return ERROR_TARGET_NOT_HALTED;
	return mchp_ri4_get_pc_value(arch_reg->target, NULL);
}

static int mchp_ri4_reg_set(struct reg *reg, uint8_t *buffer)
{
	struct mchp_ri4_reg *arch_reg = reg->arch_info;
	if (arch_reg->target->state != TARGET_HALTED)
		return ERROR_TARGET_NOT_HALTED;
	uint32_t pc = buf_get_u32(buffer, 0, reg->size);
	return mchp_ri4_set_pc_value(arch_reg->target, pc);
}

static const struct reg_arch_type mchp_ri4_reg_type = {
	.get = mchp_ri4_reg_get,
	.set = mchp_ri4_reg_set,
};

static int mchp_ri4_build_reg_cache(struct target *target)
{
	struct mchp_ri4_bridge *bridge = target_to_mchp_ri4(target);
	bridge->core_cache = calloc(1, sizeof(*bridge->core_cache));
	bridge->pc_reg = calloc(1, sizeof(*bridge->pc_reg));
	bridge->pc_value = calloc(1, 4);
	struct mchp_ri4_reg *arch_reg = calloc(1, sizeof(*arch_reg));
	if (!bridge->core_cache || !bridge->pc_reg || !bridge->pc_value || !arch_reg) {
		free(arch_reg);
		return ERROR_FAIL;
	}
	arch_reg->target = target;
	bridge->pc_reg->name = "pc";
	bridge->pc_reg->number = 0;
	bridge->pc_reg->feature = &mchp_ri4_reg_feature;
	bridge->pc_reg->value = bridge->pc_value;
	bridge->pc_reg->exist = true;
	bridge->pc_reg->size = MIN(bridge->pc_bytes, 4U) * 8U;
	bridge->pc_reg->group = "general";
	bridge->pc_reg->arch_info = arch_reg;
	bridge->pc_reg->type = &mchp_ri4_reg_type;
	bridge->core_cache->name = "mchp-ri4 registers";
	bridge->core_cache->reg_list = bridge->pc_reg;
	bridge->core_cache->num_regs = 1;
	target->reg_cache = bridge->core_cache;
	return ERROR_OK;
}

static int mchp_ri4_get_gdb_reg_list(struct target *target,
		struct reg **reg_list[], int *reg_list_size,
		enum target_register_class reg_class)
{
	(void)reg_class;
	struct mchp_ri4_bridge *bridge = target_to_mchp_ri4(target);
	struct reg **list = malloc(sizeof(*list));
	if (!list)
		return ERROR_FAIL;
	list[0] = bridge->pc_reg;
	if (target->state == TARGET_HALTED) {
		int result = mchp_ri4_reg_get(bridge->pc_reg);
		if (result != ERROR_OK) {
			free(list);
			return result;
		}
	}
	*reg_list = list;
	*reg_list_size = 1;
	return ERROR_OK;
}

static int mchp_ri4_read_memory(struct target *target, target_addr_t address,
		uint32_t size, uint32_t count, uint8_t *buffer)
{
	struct mchp_ri4_bridge *bridge = target_to_mchp_ri4(target);
	if (!bridge->caps.memory_read)
		return ERROR_TARGET_RESOURCE_NOT_AVAILABLE;
	if (size == 0 || count > UINT32_MAX / size || address > UINT32_MAX)
		return ERROR_COMMAND_ARGUMENT_INVALID;
	uint32_t length = size * count;
	char args[96];
	snprintf(args, sizeof(args), "{\"address\":%" PRIu32 ",\"size\":%" PRIu32 "}",
		(uint32_t)address, length);
	char *response = NULL;
	int result = mchp_ri4_request(bridge, "readProgram", args, &response);
	if (result != ERROR_OK)
		return result;
	const char *hex = mchp_ri4_json_value(response, "dataHex");
	if (!hex || *hex++ != '"' || strlen(hex) < (size_t)length * 2U) {
		free(response);
		return ERROR_FAIL;
	}
	for (uint32_t i = 0; i < length; i++) {
		char byte_text[3] = {hex[i * 2U], hex[i * 2U + 1U], '\0'};
		char *end = NULL;
		unsigned long value = strtoul(byte_text, &end, 16);
		if (!end || *end != '\0') {
			free(response);
			return ERROR_FAIL;
		}
		buffer[i] = (uint8_t)value;
	}
	free(response);
	return ERROR_OK;
}

static char *mchp_ri4_hex_encode(const uint8_t *data, size_t length)
{
	if (length > (SIZE_MAX - 1U) / 2U)
		return NULL;
	char *hex = malloc(length * 2U + 1U);
	if (!hex)
		return NULL;
	static const char digits[] = "0123456789abcdef";
	for (size_t i = 0; i < length; i++) {
		hex[i * 2U] = digits[data[i] >> 4];
		hex[i * 2U + 1U] = digits[data[i] & 0x0f];
	}
	hex[length * 2U] = '\0';
	return hex;
}

static int mchp_ri4_write_memory(struct target *target, target_addr_t address,
		uint32_t size, uint32_t count, const uint8_t *buffer)
{
	struct mchp_ri4_bridge *bridge = target_to_mchp_ri4(target);
	if (!bridge->caps.memory_write)
		return ERROR_TARGET_RESOURCE_NOT_AVAILABLE;
	if (size == 0 || count > UINT32_MAX / size || address > UINT32_MAX)
		return ERROR_COMMAND_ARGUMENT_INVALID;
	uint32_t length = size * count;
	char *hex = mchp_ri4_hex_encode(buffer, length);
	if (!hex)
		return ERROR_FAIL;
	size_t args_size = strlen(hex) + 96U;
	char *args = malloc(args_size);
	if (!args) {
		free(hex);
		return ERROR_FAIL;
	}
	snprintf(args, args_size, "{\"address\":%" PRIu32 ",\"dataHex\":\"%s\"}",
		(uint32_t)address, hex);
	free(hex);
	char *response = NULL;
	int result = mchp_ri4_request(bridge, "writeProgram", args, &response);
	free(args);
	free(response);
	return result;
}

static int mchp_ri4_add_breakpoint(struct target *target, struct breakpoint *breakpoint)
{
	struct mchp_ri4_bridge *bridge = target_to_mchp_ri4(target);
	if (!bridge->caps.breakpoints || breakpoint->type != BKPT_HARD || breakpoint->address > UINT32_MAX)
		return ERROR_TARGET_RESOURCE_NOT_AVAILABLE;
	char args[96];
	snprintf(args, sizeof(args), "{\"address\":%" PRIu32 ",\"kind\":%u}",
		(uint32_t)breakpoint->address, breakpoint->length);
	char *response = NULL;
	int result = mchp_ri4_request(bridge, "addBreakpoint", args, &response);
	if (result == ERROR_OK) {
		uint32_t slot = 0;
		result = mchp_ri4_json_u32(response, "slot", &slot);
		if (result == ERROR_OK)
			breakpoint_hw_set(breakpoint, slot);
	}
	free(response);
	return result;
}

static int mchp_ri4_remove_breakpoint(struct target *target, struct breakpoint *breakpoint)
{
	if (!breakpoint->is_set)
		return ERROR_OK;
	char args[112];
	snprintf(args, sizeof(args), "{\"address\":%" PRIu32 ",\"slot\":%u}",
		(uint32_t)breakpoint->address, breakpoint->number);
	char *response = NULL;
	int result = mchp_ri4_request(target_to_mchp_ri4(target), "removeBreakpoint", args, &response);
	free(response);
	if (result == ERROR_OK)
		breakpoint->is_set = false;
	return result;
}

static const char *mchp_ri4_watch_access(enum watchpoint_rw rw)
{
	switch (rw) {
	case WPT_READ: return "read";
	case WPT_WRITE: return "write";
	case WPT_ACCESS: return "access";
	default: return NULL;
	}
}

static int mchp_ri4_add_watchpoint(struct target *target, struct watchpoint *watchpoint)
{
	struct mchp_ri4_bridge *bridge = target_to_mchp_ri4(target);
	const char *access = mchp_ri4_watch_access(watchpoint->rw);
	if (!bridge->caps.watchpoints || !access || watchpoint->address > UINT32_MAX)
		return ERROR_TARGET_RESOURCE_NOT_AVAILABLE;
	char args[128];
	snprintf(args, sizeof(args),
		"{\"address\":%" PRIu32 ",\"length\":%u,\"access\":\"%s\"}",
		(uint32_t)watchpoint->address, watchpoint->length, access);
	char *response = NULL;
	int result = mchp_ri4_request(bridge, "addWatchpoint", args, &response);
	if (result == ERROR_OK) {
		uint32_t slot = 0;
		result = mchp_ri4_json_u32(response, "slot", &slot);
		if (result == ERROR_OK)
			watchpoint_set(watchpoint, slot);
	}
	free(response);
	return result;
}

static int mchp_ri4_remove_watchpoint(struct target *target, struct watchpoint *watchpoint)
{
	if (!watchpoint->is_set)
		return ERROR_OK;
	char args[112];
	snprintf(args, sizeof(args), "{\"address\":%" PRIu32 ",\"slot\":%u}",
		(uint32_t)watchpoint->address, watchpoint->number);
	char *response = NULL;
	int result = mchp_ri4_request(target_to_mchp_ri4(target), "removeWatchpoint", args, &response);
	free(response);
	if (result == ERROR_OK)
		watchpoint->is_set = false;
	return result;
}

static int mchp_ri4_target_create(struct target *target)
{
	struct mchp_ri4_bridge *bridge = calloc(1, sizeof(*bridge));
	if (!bridge)
		return ERROR_FAIL;
	bridge->host = strdup(MCHP_RI4_DEFAULT_HOST);
	bridge->port = MCHP_RI4_DEFAULT_PORT;
	bridge->tool = strdup("pk4");
	bridge->family = strdup("");
	bridge->processor = strdup("");
	bridge->scripts_path = strdup("");
	bridge->tool_scripts_path = strdup("");
	bridge->script_suffix = strdup("");
	bridge->serial_number = strdup("");
	bridge->pc_bytes = 4;
	bridge->sock = -1;
	if (!bridge->host || !bridge->tool || !bridge->family || !bridge->processor ||
			!bridge->scripts_path || !bridge->tool_scripts_path ||
			!bridge->script_suffix || !bridge->serial_number) {
		free(bridge);
		return ERROR_FAIL;
	}
	target->arch_info = bridge;
	return ERROR_OK;
}

static int mchp_ri4_init_target(struct command_context *cmd_ctx, struct target *target)
{
	(void)cmd_ctx;
	return mchp_ri4_build_reg_cache(target);
}

static int mchp_ri4_examine(struct target *target)
{
	struct mchp_ri4_bridge *bridge = target_to_mchp_ri4(target);
	int result = mchp_ri4_start_session(bridge);
	if (result != ERROR_OK)
		return result;
	result = mchp_ri4_refresh_capabilities(bridge);
	if (result != ERROR_OK)
		return result;
	if (!bridge->caps.debug) {
		LOG_ERROR("mchp_ri4: selected script pack does not expose complete debug controls");
		return ERROR_TARGET_RESOURCE_NOT_AVAILABLE;
	}
	result = mchp_ri4_simple_request(target, "enterDebugMode");
	if (result != ERROR_OK)
		return result;
	target->state = TARGET_HALTED;
	target->debug_reason = DBG_REASON_DBGRQ;
	return mchp_ri4_get_pc_value(target, NULL);
}

static void mchp_ri4_deinit_target(struct target *target)
{
	struct mchp_ri4_bridge *bridge = target_to_mchp_ri4(target);
	if (!bridge)
		return;
	mchp_ri4_end_session(bridge);
	if (bridge->pc_reg)
		free(bridge->pc_reg->arch_info);
	free(bridge->pc_value);
	free(bridge->pc_reg);
	free(bridge->core_cache);
	free(bridge->host);
	free(bridge->tool);
	free(bridge->family);
	free(bridge->processor);
	free(bridge->scripts_path);
	free(bridge->tool_scripts_path);
	free(bridge->script_suffix);
	free(bridge->serial_number);
	free(bridge);
	target->arch_info = NULL;
	target->reg_cache = NULL;
}

COMMAND_HANDLER(mchp_ri4_handle_configure)
{
	if (CMD_ARGC < 1)
		return ERROR_COMMAND_SYNTAX_ERROR;
	struct target *target = get_target(CMD_ARGV[0]);
	if (!mchp_ri4_bridge_is_target(target)) {
		command_print(CMD, "target '%s' is not an mchp_ri4_bridge target", CMD_ARGV[0]);
		return ERROR_COMMAND_ARGUMENT_INVALID;
	}
	struct mchp_ri4_bridge *bridge = target_to_mchp_ri4(target);
	for (unsigned int i = 1; i < CMD_ARGC; i++) {
		const char *option = CMD_ARGV[i];
		if (i + 1 >= CMD_ARGC)
			return ERROR_COMMAND_SYNTAX_ERROR;
		const char *value = CMD_ARGV[++i];
		uint32_t number = 0;
		if (strcmp(option, "-host") == 0)
			mchp_ri4_replace_string(&bridge->host, value);
		else if (strcmp(option, "-port") == 0) {
			if (mchp_ri4_parse_u32(value, &number) != ERROR_OK || number > 65535)
				return ERROR_COMMAND_ARGUMENT_INVALID;
			bridge->port = number;
		} else if (strcmp(option, "-tool") == 0)
			mchp_ri4_replace_string(&bridge->tool, value);
		else if (strcmp(option, "-vid") == 0) {
			if (mchp_ri4_parse_u32(value, &number) != ERROR_OK || number > UINT16_MAX)
				return ERROR_COMMAND_ARGUMENT_INVALID;
			bridge->vid = number;
		} else if (strcmp(option, "-pid") == 0) {
			if (mchp_ri4_parse_u32(value, &number) != ERROR_OK || number > UINT16_MAX)
				return ERROR_COMMAND_ARGUMENT_INVALID;
			bridge->pid = number;
		} else if (strcmp(option, "-family") == 0)
			mchp_ri4_replace_string(&bridge->family, value);
		else if (strcmp(option, "-processor") == 0)
			mchp_ri4_replace_string(&bridge->processor, value);
		else if (strcmp(option, "-scripts") == 0)
			mchp_ri4_replace_string(&bridge->scripts_path, value);
		else if (strcmp(option, "-tool-scripts") == 0)
			mchp_ri4_replace_string(&bridge->tool_scripts_path, value);
		else if (strcmp(option, "-script-suffix") == 0)
			mchp_ri4_replace_string(&bridge->script_suffix, value);
		else if (strcmp(option, "-serial") == 0)
			mchp_ri4_replace_string(&bridge->serial_number, value);
		else if (strcmp(option, "-pc-bytes") == 0) {
			if (mchp_ri4_parse_u32(value, &number) != ERROR_OK || number == 0 || number > 4)
				return ERROR_COMMAND_ARGUMENT_INVALID;
			bridge->pc_bytes = number;
		} else {
			command_print(CMD, "unknown mchp_ri4 configure option: %s", option);
			return ERROR_COMMAND_ARGUMENT_INVALID;
		}
	}
	return ERROR_OK;
}

static int mchp_ri4_command_target(const char *name, struct target **target_out)
{
	struct target *target = get_target(name);
	if (!mchp_ri4_bridge_is_target(target))
		return ERROR_COMMAND_ARGUMENT_INVALID;
	*target_out = target;
	return ERROR_OK;
}

COMMAND_HANDLER(mchp_ri4_handle_capabilities)
{
	if (CMD_ARGC != 1)
		return ERROR_COMMAND_SYNTAX_ERROR;
	struct target *target = NULL;
	if (mchp_ri4_command_target(CMD_ARGV[0], &target) != ERROR_OK)
		return ERROR_COMMAND_ARGUMENT_INVALID;
	struct mchp_ri4_bridge *bridge = target_to_mchp_ri4(target);
	int result = mchp_ri4_refresh_capabilities(bridge);
	if (result != ERROR_OK)
		return result;
	command_print(CMD,
		"flash=%d erase=%d verify=%d debug=%d poll=%d set_pc=%d breakpoints=%d watchpoints=%d memory_read=%d memory_write=%d",
		bridge->caps.flash, bridge->caps.erase, bridge->caps.verify,
		bridge->caps.debug, bridge->caps.poll, bridge->caps.set_pc,
		bridge->caps.breakpoints, bridge->caps.watchpoints,
		bridge->caps.memory_read, bridge->caps.memory_write);
	return ERROR_OK;
}

int mchp_ri4_bridge_mass_erase(struct target *target, unsigned int mode)
{
	if (!mchp_ri4_bridge_is_target(target))
		return ERROR_COMMAND_ARGUMENT_INVALID;
	struct mchp_ri4_bridge *bridge = target_to_mchp_ri4(target);
	if (!bridge || !bridge->caps.erase)
		return ERROR_TARGET_RESOURCE_NOT_AVAILABLE;
	char args[64];
	snprintf(args, sizeof(args), "{\"mode\":%u}", mode);
	char *response = NULL;
	int result = mchp_ri4_request(bridge, "erase", args, &response);
	free(response);
	return result;
}

COMMAND_HANDLER(mchp_ri4_handle_erase)
{
	if (CMD_ARGC < 1 || CMD_ARGC > 2)
		return ERROR_COMMAND_SYNTAX_ERROR;
	struct target *target = NULL;
	if (mchp_ri4_command_target(CMD_ARGV[0], &target) != ERROR_OK)
		return ERROR_COMMAND_ARGUMENT_INVALID;
	uint32_t mode = 0;
	if (CMD_ARGC == 2 && mchp_ri4_parse_u32(CMD_ARGV[1], &mode) != ERROR_OK)
		return ERROR_COMMAND_ARGUMENT_INVALID;
	return mchp_ri4_bridge_mass_erase(target, mode);
}

static int mchp_ri4_path_request(struct target *target, const char *command,
		const char *path, bool verify)
{
	char *escaped = mchp_ri4_json_escape(path);
	if (!escaped)
		return ERROR_FAIL;
	size_t args_size = strlen(escaped) + 96U;
	char *args = malloc(args_size);
	if (!args) {
		free(escaped);
		return ERROR_FAIL;
	}
	if (strcmp(command, "programHex") == 0)
		snprintf(args, args_size,
			"{\"path\":\"%s\",\"eraseFirst\":true,\"verify\":%s}",
			escaped, verify ? "true" : "false");
	else
		snprintf(args, args_size, "{\"path\":\"%s\"}", escaped);
	free(escaped);
	char *response = NULL;
	int result = mchp_ri4_request(target_to_mchp_ri4(target), command, args, &response);
	free(args);
	free(response);
	return result;
}

COMMAND_HANDLER(mchp_ri4_handle_program)
{
	if (CMD_ARGC < 2 || CMD_ARGC > 3)
		return ERROR_COMMAND_SYNTAX_ERROR;
	struct target *target = NULL;
	if (mchp_ri4_command_target(CMD_ARGV[0], &target) != ERROR_OK)
		return ERROR_COMMAND_ARGUMENT_INVALID;
	bool verify = CMD_ARGC == 3 && strcmp(CMD_ARGV[2], "verify") == 0;
	if (CMD_ARGC == 3 && !verify)
		return ERROR_COMMAND_ARGUMENT_INVALID;
	return mchp_ri4_path_request(target, "programHex", CMD_ARGV[1], verify);
}

COMMAND_HANDLER(mchp_ri4_handle_verify)
{
	if (CMD_ARGC != 2)
		return ERROR_COMMAND_SYNTAX_ERROR;
	struct target *target = NULL;
	if (mchp_ri4_command_target(CMD_ARGV[0], &target) != ERROR_OK)
		return ERROR_COMMAND_ARGUMENT_INVALID;
	return mchp_ri4_path_request(target, "verifyHex", CMD_ARGV[1], false);
}

static const struct command_registration mchp_ri4_exec_command_handlers[] = {
	{
		.name = "configure",
		.handler = mchp_ri4_handle_configure,
		.mode = COMMAND_CONFIG,
		.help = "configure a Microchip RI4 bridge target",
		.usage = "target [-host host] [-port port] [-tool pk4|icd4] [-vid id] [-pid id] "
			"[-family name] -processor name -scripts path [-tool-scripts path] "
			"[-script-suffix suffix] [-serial serial] [-pc-bytes 1..4]",
	},
	{
		.name = "capabilities",
		.handler = mchp_ri4_handle_capabilities,
		.mode = COMMAND_EXEC,
		.help = "show capabilities reported by the active script pack",
		.usage = "target",
	},
	{
		.name = "erase",
		.handler = mchp_ri4_handle_erase,
		.mode = COMMAND_EXEC,
		.help = "erase the selected target through the RI4 bridge",
		.usage = "target [mode]",
	},
	{
		.name = "program",
		.handler = mchp_ri4_handle_program,
		.mode = COMMAND_EXEC,
		.help = "program an Intel HEX image through the RI4 bridge",
		.usage = "target image.hex [verify]",
	},
	{
		.name = "verify",
		.handler = mchp_ri4_handle_verify,
		.mode = COMMAND_EXEC,
		.help = "verify an Intel HEX image through the RI4 bridge",
		.usage = "target image.hex",
	},
	COMMAND_REGISTRATION_DONE
};

static const struct command_registration mchp_ri4_command_handlers[] = {
	{
		.name = "mchp_ri4",
		.mode = COMMAND_ANY,
		.help = "Microchip PICkit 4 / ICD 4 RI4 bridge commands",
		.usage = "",
		.chain = mchp_ri4_exec_command_handlers,
	},
	COMMAND_REGISTRATION_DONE
};

struct target_type mchp_ri4_bridge_target = {
	.name = MCHP_RI4_TARGET_NAME,
	.commands = mchp_ri4_command_handlers,
	.poll = mchp_ri4_poll,
	.halt = mchp_ri4_halt,
	.resume = mchp_ri4_resume,
	.step = mchp_ri4_step,
	.assert_reset = mchp_ri4_assert_reset,
	.deassert_reset = mchp_ri4_deassert_reset,
	.soft_reset_halt = mchp_ri4_soft_reset_halt,
	.get_gdb_reg_list = mchp_ri4_get_gdb_reg_list,
	.get_gdb_reg_list_noread = mchp_ri4_get_gdb_reg_list,
	.read_memory = mchp_ri4_read_memory,
	.write_memory = mchp_ri4_write_memory,
	.add_breakpoint = mchp_ri4_add_breakpoint,
	.remove_breakpoint = mchp_ri4_remove_breakpoint,
	.add_watchpoint = mchp_ri4_add_watchpoint,
	.remove_watchpoint = mchp_ri4_remove_watchpoint,
	.target_create = mchp_ri4_target_create,
	.init_target = mchp_ri4_init_target,
	.examine = mchp_ri4_examine,
	.deinit_target = mchp_ri4_deinit_target,
};
