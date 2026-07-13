// SPDX-License-Identifier: GPL-2.0-or-later

#ifdef HAVE_CONFIG_H
#include "config.h"
#endif

#ifdef HAVE_NETDB_H
#include <netdb.h>
#endif
#ifdef HAVE_NETINET_TCP_H
#include <netinet/tcp.h>
#endif
#ifdef HAVE_SYS_SOCKET_H
#include <sys/socket.h>
#endif
#ifdef _WIN32
#include <winsock2.h>
#include <ws2tcpip.h>
#endif

#include <ctype.h>
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <helper/command.h>
#include <helper/log.h>
#include <helper/replacements.h>
#include <helper/system.h>

#include "breakpoints.h"
#include "target.h"
#include "target_type.h"

#define RI4_RESPONSE_SIZE (256 * 1024)

struct mchp_ri4_bridge {
	char *host;
	char *port;
	char *tool;
	char *family;
	char *processor;
	char *scripts_path;
	char *tool_scripts_path;
	char *script_suffix;
	uint32_t vid;
	uint32_t pid;
	uint32_t pc_bytes;
	int sock;
	bool session_started;
};

static char ri4_default_host[] = "127.0.0.1";
static char ri4_default_port[] = "9123";
static char ri4_default_tool[] = "pk4";

static struct mchp_ri4_bridge ri4_config = {
	.host = ri4_default_host,
	.port = ri4_default_port,
	.tool = ri4_default_tool,
	.pc_bytes = 4,
	.sock = -1,
};

static char *ri4_strdup(const char *value)
{
	const char *source = value ? value : "";
	size_t length = strlen(source) + 1;
	char *copy = malloc(length);
	if (copy)
		memcpy(copy, source, length);
	if (!copy)
		LOG_ERROR("mchp_ri4_bridge: out of memory");
	return copy;
}

static void ri4_replace_string(char **field, const char *value)
{
	if (*field && *field != ri4_default_host && *field != ri4_default_port && *field != ri4_default_tool)
		free(*field);
	*field = ri4_strdup(value);
}

static int ri4_connect(struct mchp_ri4_bridge *bridge)
{
	if (bridge->sock >= 0)
		return ERROR_OK;

	struct addrinfo hints = {
		.ai_family = AF_UNSPEC,
		.ai_socktype = SOCK_STREAM,
	};
	struct addrinfo *addresses = NULL;
	int status = getaddrinfo(bridge->host, bridge->port, &hints, &addresses);
	if (status != 0) {
		LOG_ERROR("mchp_ri4_bridge: getaddrinfo(%s:%s): %s",
				bridge->host, bridge->port, gai_strerror(status));
		return ERROR_FAIL;
	}

	for (struct addrinfo *address = addresses; address; address = address->ai_next) {
		int sock = socket(address->ai_family, address->ai_socktype, address->ai_protocol);
		if (sock < 0)
			continue;
		if (connect(sock, address->ai_addr, address->ai_addrlen) == 0) {
			bridge->sock = sock;
			break;
		}
		close_socket(sock);
	}
	freeaddrinfo(addresses);
	if (bridge->sock < 0) {
		LOG_ERROR("mchp_ri4_bridge: cannot connect to %s:%s", bridge->host, bridge->port);
		return ERROR_FAIL;
	}
	int one = 1;
	setsockopt(bridge->sock, IPPROTO_TCP, TCP_NODELAY, (const char *)&one, sizeof(one));
	return ERROR_OK;
}

static void ri4_disconnect(struct mchp_ri4_bridge *bridge)
{
	if (bridge->sock >= 0)
		close_socket(bridge->sock);
	bridge->sock = -1;
	bridge->session_started = false;
}

static int ri4_send_all(int sock, const char *data, size_t length)
{
	while (length) {
		int sent = write_socket(sock, data, (unsigned int)length);
		if (sent <= 0)
			return ERROR_FAIL;
		data += sent;
		length -= (size_t)sent;
	}
	return ERROR_OK;
}

static int ri4_request(struct mchp_ri4_bridge *bridge, const char *request,
		char *response, size_t response_size)
{
	if (ri4_connect(bridge) != ERROR_OK)
		return ERROR_FAIL;
	if (ri4_send_all(bridge->sock, request, strlen(request)) != ERROR_OK ||
			ri4_send_all(bridge->sock, "\n", 1) != ERROR_OK) {
		ri4_disconnect(bridge);
		return ERROR_FAIL;
	}

	size_t used = 0;
	while (used + 1 < response_size) {
		char value;
		int received = read_socket(bridge->sock, &value, 1);
		if (received <= 0) {
			ri4_disconnect(bridge);
			return ERROR_FAIL;
		}
		if (value == '\n')
			break;
		response[used++] = value;
	}
	response[used] = '\0';
	if (!strstr(response, "\"ok\": true") && !strstr(response, "\"ok\":true")) {
		LOG_ERROR("mchp_ri4_bridge request failed: %s", response);
		return ERROR_FAIL;
	}
	return ERROR_OK;
}

static char *ri4_json_escape(const char *input)
{
	size_t length = 1;
	for (const unsigned char *p = (const unsigned char *)input; *p; ++p)
		length += (*p == '"' || *p == '\\' || *p < 0x20) ? 2 : 1;
	char *escaped = malloc(length);
	if (!escaped)
		return NULL;
	char *out = escaped;
	for (const unsigned char *p = (const unsigned char *)input; *p; ++p) {
		if (*p == '"' || *p == '\\') {
			*out++ = '\\';
			*out++ = (char)*p;
		} else if (*p < 0x20) {
			*out++ = ' ';
		} else {
			*out++ = (char)*p;
		}
	}
	*out = '\0';
	return escaped;
}

static int ri4_simple_command(struct mchp_ri4_bridge *bridge, const char *command)
{
	char request[128];
	char response[1024];
	snprintf(request, sizeof(request), "{\"command\":\"%s\",\"args\":{}}", command);
	return ri4_request(bridge, request, response, sizeof(response));
}

static int ri4_start_session(struct mchp_ri4_bridge *bridge)
{
	if (bridge->session_started)
		return ERROR_OK;
	if (!bridge->processor || !*bridge->processor || !bridge->scripts_path || !*bridge->scripts_path) {
		LOG_ERROR("mchp_ri4_bridge: processor and scripts_path must be configured");
		return ERROR_FAIL;
	}
	char *processor = ri4_json_escape(bridge->processor);
	char *scripts = ri4_json_escape(bridge->scripts_path);
	char *tool_scripts = ri4_json_escape(bridge->tool_scripts_path ? bridge->tool_scripts_path : "");
	char *suffix = ri4_json_escape(bridge->script_suffix ? bridge->script_suffix : "");
	char *family = ri4_json_escape(bridge->family ? bridge->family : "");
	if (!processor || !scripts || !tool_scripts || !suffix || !family) {
		free(processor); free(scripts); free(tool_scripts); free(suffix); free(family);
		return ERROR_FAIL;
	}
	char request[4096];
	char response[8192];
	snprintf(request, sizeof(request),
			"{\"command\":\"startSession\",\"args\":{\"tool\":\"%s\","
			"\"vid\":%" PRIu32 ",\"pid\":%" PRIu32 ",\"processor\":\"%s\","
			"\"scriptsPath\":\"%s\",\"toolScriptsPath\":\"%s\","
			"\"scriptSuffix\":\"%s\",\"family\":\"%s\",\"pcBytes\":%" PRIu32 "}}",
			bridge->tool, bridge->vid, bridge->pid, processor, scripts, tool_scripts,
			suffix, family, bridge->pc_bytes);
	free(processor); free(scripts); free(tool_scripts); free(suffix); free(family);
	if (ri4_request(bridge, request, response, sizeof(response)) != ERROR_OK)
		return ERROR_FAIL;
	bridge->session_started = true;
	return ri4_simple_command(bridge, "enterDebugMode");
}

static int ri4_extract_int(const char *response, const char *name, unsigned int *value)
{
	char key[64];
	snprintf(key, sizeof(key), "\"%s\"", name);
	const char *position = strstr(response, key);
	if (!position || !(position = strchr(position + strlen(key), ':')))
		return ERROR_FAIL;
	char *end = NULL;
	unsigned long parsed = strtoul(position + 1, &end, 0);
	if (end == position + 1)
		return ERROR_FAIL;
	*value = (unsigned int)parsed;
	return ERROR_OK;
}

static int ri4_extract_bool(const char *response, const char *name, bool *value)
{
	char key[64];
	snprintf(key, sizeof(key), "\"%s\"", name);
	const char *position = strstr(response, key);
	if (!position || !(position = strchr(position + strlen(key), ':')))
		return ERROR_FAIL;
	++position;
	while (isspace((unsigned char)*position))
		++position;
	if (strncmp(position, "true", 4) == 0) {
		*value = true;
		return ERROR_OK;
	}
	if (strncmp(position, "false", 5) == 0) {
		*value = false;
		return ERROR_OK;
	}
	return ERROR_FAIL;
}

static int ri4_hex_nibble(char value)
{
	if (value >= '0' && value <= '9') return value - '0';
	if (value >= 'a' && value <= 'f') return value - 'a' + 10;
	if (value >= 'A' && value <= 'F') return value - 'A' + 10;
	return -1;
}

static int ri4_extract_hex(const char *response, const char *name, uint8_t *buffer, size_t length)
{
	char key[64];
	snprintf(key, sizeof(key), "\"%s\"", name);
	const char *position = strstr(response, key);
	if (!position || !(position = strchr(position + strlen(key), ':')) || !(position = strchr(position, '"')))
		return ERROR_FAIL;
	++position;
	for (size_t i = 0; i < length; ++i) {
		int high = ri4_hex_nibble(position[i * 2]);
		int low = ri4_hex_nibble(position[i * 2 + 1]);
		if (high < 0 || low < 0)
			return ERROR_FAIL;
		buffer[i] = (uint8_t)((high << 4) | low);
	}
	return ERROR_OK;
}

static char *ri4_encode_hex(const uint8_t *buffer, size_t length)
{
	static const char digits[] = "0123456789abcdef";
	char *result = malloc(length * 2 + 1);
	if (!result)
		return NULL;
	for (size_t i = 0; i < length; ++i) {
		result[i * 2] = digits[buffer[i] >> 4];
		result[i * 2 + 1] = digits[buffer[i] & 0x0f];
	}
	result[length * 2] = '\0';
	return result;
}

static int ri4_init_target(struct command_context *cmd_ctx, struct target *target)
{
	(void)cmd_ctx;
	target->state = TARGET_UNKNOWN;
	target->debug_reason = DBG_REASON_UNDEFINED;
	return ERROR_OK;
}

static int ri4_target_create(struct target *target)
{
	struct mchp_ri4_bridge *bridge = calloc(1, sizeof(*bridge));
	if (!bridge)
		return ERROR_FAIL;
	bridge->host = ri4_strdup(ri4_config.host);
	bridge->port = ri4_strdup(ri4_config.port);
	bridge->tool = ri4_strdup(ri4_config.tool);
	bridge->family = ri4_strdup(ri4_config.family);
	bridge->processor = ri4_strdup(ri4_config.processor);
	bridge->scripts_path = ri4_strdup(ri4_config.scripts_path);
	bridge->tool_scripts_path = ri4_strdup(ri4_config.tool_scripts_path);
	bridge->script_suffix = ri4_strdup(ri4_config.script_suffix);
	bridge->vid = ri4_config.vid;
	bridge->pid = ri4_config.pid;
	bridge->pc_bytes = ri4_config.pc_bytes;
	bridge->sock = -1;
	target->arch_info = bridge;
	return ERROR_OK;
}

static void ri4_deinit_target(struct target *target)
{
	struct mchp_ri4_bridge *bridge = target->arch_info;
	if (!bridge)
		return;
	if (bridge->session_started)
		ri4_simple_command(bridge, "endSession");
	ri4_disconnect(bridge);
	free(bridge->host); free(bridge->port); free(bridge->tool); free(bridge->family);
	free(bridge->processor); free(bridge->scripts_path); free(bridge->tool_scripts_path);
	free(bridge->script_suffix); free(bridge);
}

static int ri4_examine(struct target *target)
{
	struct mchp_ri4_bridge *bridge = target->arch_info;
	if (ri4_start_session(bridge) != ERROR_OK)
		return ERROR_FAIL;
	target->state = TARGET_HALTED;
	target->debug_reason = DBG_REASON_DBGRQ;
	target_set_examined(target);
	return ERROR_OK;
}

static int ri4_poll(struct target *target)
{
	struct mchp_ri4_bridge *bridge = target->arch_info;
	char response[2048];
	if (ri4_request(bridge, "{\"command\":\"targetStatus\",\"args\":{}}",
			response, sizeof(response)) != ERROR_OK)
		return ERROR_FAIL;
	bool halted;
	if (ri4_extract_bool(response, "halted", &halted) != ERROR_OK)
		return ERROR_FAIL;
	if (halted && target->state != TARGET_HALTED) {
		target->state = TARGET_HALTED;
		target->debug_reason = target->watchpoints ? DBG_REASON_WATCHPOINT :
				target->breakpoints ? DBG_REASON_BREAKPOINT : DBG_REASON_DBGRQ;
		target_call_event_callbacks(target, TARGET_EVENT_HALTED);
	} else if (!halted && target->state == TARGET_HALTED) {
		target->state = TARGET_RUNNING;
		target->debug_reason = DBG_REASON_NOTHALTED;
	}
	return ERROR_OK;
}

static int ri4_halt(struct target *target)
{
	if (ri4_simple_command(target->arch_info, "halt") != ERROR_OK)
		return ERROR_FAIL;
	target->state = TARGET_HALTED;
	target->debug_reason = DBG_REASON_DBGRQ;
	target_call_event_callbacks(target, TARGET_EVENT_HALTED);
	return ERROR_OK;
}

static int ri4_set_pc(struct mchp_ri4_bridge *bridge, target_addr_t address)
{
	char request[192];
	char response[1024];
	snprintf(request, sizeof(request),
			"{\"command\":\"setPc\",\"args\":{\"address\":%" PRIu64 "}}",
			(uint64_t)address);
	return ri4_request(bridge, request, response, sizeof(response));
}

static int ri4_resume(struct target *target, bool current, target_addr_t address,
		bool handle_breakpoints, bool debug_execution)
{
	(void)handle_breakpoints;
	struct mchp_ri4_bridge *bridge = target->arch_info;
	if (!current && ri4_set_pc(bridge, address) != ERROR_OK)
		return ERROR_FAIL;
	if (ri4_simple_command(bridge, "run") != ERROR_OK)
		return ERROR_FAIL;
	target->state = debug_execution ? TARGET_DEBUG_RUNNING : TARGET_RUNNING;
	target->debug_reason = DBG_REASON_NOTHALTED;
	target_call_event_callbacks(target, TARGET_EVENT_RESUMED);
	return ERROR_OK;
}

static int ri4_step(struct target *target, bool current, target_addr_t address,
		bool handle_breakpoints)
{
	(void)handle_breakpoints;
	struct mchp_ri4_bridge *bridge = target->arch_info;
	if (!current && ri4_set_pc(bridge, address) != ERROR_OK)
		return ERROR_FAIL;
	if (ri4_simple_command(bridge, "step") != ERROR_OK)
		return ERROR_FAIL;
	target->state = TARGET_HALTED;
	target->debug_reason = DBG_REASON_SINGLESTEP;
	target_call_event_callbacks(target, TARGET_EVENT_HALTED);
	return ERROR_OK;
}

static int ri4_read_memory(struct target *target, target_addr_t address,
		uint32_t size, uint32_t count, uint8_t *buffer)
{
	size_t length = (size_t)size * count;
	char request[256];
	char *response = malloc(RI4_RESPONSE_SIZE);
	if (!response || length > (RI4_RESPONSE_SIZE / 2 - 256)) {
		free(response);
		return ERROR_FAIL;
	}
	snprintf(request, sizeof(request),
			"{\"command\":\"readProgram\",\"args\":{\"address\":%" PRIu64 ",\"size\":%zu}}",
			(uint64_t)address, length);
	int result = ri4_request(target->arch_info, request, response, RI4_RESPONSE_SIZE);
	if (result == ERROR_OK)
		result = ri4_extract_hex(response, "dataHex", buffer, length);
	free(response);
	return result;
}

static int ri4_write_memory(struct target *target, target_addr_t address,
		uint32_t size, uint32_t count, const uint8_t *buffer)
{
	size_t length = (size_t)size * count;
	char *hex = ri4_encode_hex(buffer, length);
	if (!hex)
		return ERROR_FAIL;
	size_t request_size = strlen(hex) + 256;
	char *request = malloc(request_size);
	char response[2048];
	if (!request) {
		free(hex);
		return ERROR_FAIL;
	}
	snprintf(request, request_size,
			"{\"command\":\"writeProgram\",\"args\":{\"address\":%" PRIu64 ",\"dataHex\":\"%s\"}}",
			(uint64_t)address, hex);
	int result = ri4_request(target->arch_info, request, response, sizeof(response));
	free(request);
	free(hex);
	return result;
}

static int ri4_add_breakpoint(struct target *target, struct breakpoint *breakpoint)
{
	char request[256];
	char response[2048];
	snprintf(request, sizeof(request),
			"{\"command\":\"setBreakpoint\",\"args\":{\"address\":%" PRIu64 "}}",
			(uint64_t)breakpoint->address);
	if (ri4_request(target->arch_info, request, response, sizeof(response)) != ERROR_OK)
		return ERROR_TARGET_RESOURCE_NOT_AVAILABLE;
	unsigned int slot;
	if (ri4_extract_int(response, "slot", &slot) != ERROR_OK)
		return ERROR_FAIL;
	breakpoint_hw_set(breakpoint, slot);
	return ERROR_OK;
}

static int ri4_clear_slot(struct target *target, unsigned int slot)
{
	char request[192];
	char response[2048];
	snprintf(request, sizeof(request),
			"{\"command\":\"clearHardwarePoint\",\"args\":{\"slot\":%u}}", slot);
	return ri4_request(target->arch_info, request, response, sizeof(response));
}

static int ri4_remove_breakpoint(struct target *target, struct breakpoint *breakpoint)
{
	if (!breakpoint->is_set)
		return ERROR_OK;
	int result = ri4_clear_slot(target, breakpoint->number);
	if (result == ERROR_OK)
		breakpoint->is_set = false;
	return result;
}

static int ri4_add_watchpoint(struct target *target, struct watchpoint *watchpoint)
{
	const char *access = watchpoint->rw == WPT_READ ? "read" :
			watchpoint->rw == WPT_WRITE ? "write" : "access";
	char request[320];
	char response[2048];
	snprintf(request, sizeof(request),
			"{\"command\":\"setWatchpoint\",\"args\":{\"address\":%" PRIu64 ","
			"\"length\":%u,\"access\":\"%s\"}}",
			(uint64_t)watchpoint->address, watchpoint->length, access);
	if (ri4_request(target->arch_info, request, response, sizeof(response)) != ERROR_OK)
		return ERROR_TARGET_RESOURCE_NOT_AVAILABLE;
	unsigned int slot;
	if (ri4_extract_int(response, "slot", &slot) != ERROR_OK)
		return ERROR_FAIL;
	watchpoint_set(watchpoint, slot);
	return ERROR_OK;
}

static int ri4_remove_watchpoint(struct target *target, struct watchpoint *watchpoint)
{
	if (!watchpoint->is_set)
		return ERROR_OK;
	int result = ri4_clear_slot(target, watchpoint->number);
	if (result == ERROR_OK)
		watchpoint->is_set = false;
	return result;
}

COMMAND_HANDLER(ri4_handle_host)
{
	if (CMD_ARGC != 1)
		return ERROR_COMMAND_SYNTAX_ERROR;
	ri4_replace_string(&ri4_config.host, CMD_ARGV[0]);
	return ERROR_OK;
}

COMMAND_HANDLER(ri4_handle_port)
{
	if (CMD_ARGC != 1)
		return ERROR_COMMAND_SYNTAX_ERROR;
	ri4_replace_string(&ri4_config.port, CMD_ARGV[0]);
	return ERROR_OK;
}

COMMAND_HANDLER(ri4_handle_session)
{
	if (CMD_ARGC < 6 || CMD_ARGC > 9)
		return ERROR_COMMAND_SYNTAX_ERROR;
	ri4_replace_string(&ri4_config.tool, CMD_ARGV[0]);
	COMMAND_PARSE_NUMBER(u32, CMD_ARGV[1], ri4_config.vid);
	COMMAND_PARSE_NUMBER(u32, CMD_ARGV[2], ri4_config.pid);
	ri4_replace_string(&ri4_config.processor, CMD_ARGV[3]);
	ri4_replace_string(&ri4_config.scripts_path, CMD_ARGV[4]);
	ri4_replace_string(&ri4_config.family, CMD_ARGV[5]);
	if (CMD_ARGC > 6) ri4_replace_string(&ri4_config.tool_scripts_path, CMD_ARGV[6]);
	if (CMD_ARGC > 7) ri4_replace_string(&ri4_config.script_suffix, CMD_ARGV[7]);
	if (CMD_ARGC > 8) COMMAND_PARSE_NUMBER(u32, CMD_ARGV[8], ri4_config.pc_bytes);
	return ERROR_OK;
}

static int ri4_file_command(struct command_invocation *cmd, const char *command,
		const char *path, bool verify)
{
	struct target *target = get_current_target(CMD_CTX);
	struct mchp_ri4_bridge *bridge = target->arch_info;
	char *escaped = ri4_json_escape(path);
	if (!escaped)
		return ERROR_FAIL;
	size_t request_size = strlen(escaped) + 256;
	char *request = malloc(request_size);
	char response[8192];
	if (!request) {
		free(escaped);
		return ERROR_FAIL;
	}
	snprintf(request, request_size,
			"{\"command\":\"%s\",\"args\":{\"path\":\"%s\",\"verify\":%s}}",
			command, escaped, verify ? "true" : "false");
	int result = ri4_request(bridge, request, response, sizeof(response));
	if (result == ERROR_OK)
		command_print(cmd, "%s", response);
	free(request);
	free(escaped);
	return result;
}

COMMAND_HANDLER(ri4_handle_erase)
{
	if (CMD_ARGC != 0)
		return ERROR_COMMAND_SYNTAX_ERROR;
	return ri4_simple_command(get_current_target(CMD_CTX)->arch_info, "eraseChip");
}

COMMAND_HANDLER(ri4_handle_program)
{
	if (CMD_ARGC < 1 || CMD_ARGC > 2)
		return ERROR_COMMAND_SYNTAX_ERROR;
	bool verify = CMD_ARGC == 2 && strcmp(CMD_ARGV[1], "verify") == 0;
	return ri4_file_command(CMD, "programHex", CMD_ARGV[0], verify);
}

COMMAND_HANDLER(ri4_handle_verify)
{
	if (CMD_ARGC != 1)
		return ERROR_COMMAND_SYNTAX_ERROR;
	return ri4_file_command(CMD, "verifyHex", CMD_ARGV[0], true);
}

static const struct command_registration ri4_subcommands[] = {
	{ .name = "host", .handler = ri4_handle_host, .mode = COMMAND_CONFIG,
		.help = "set RI4 bridge host", .usage = "hostname" },
	{ .name = "port", .handler = ri4_handle_port, .mode = COMMAND_CONFIG,
		.help = "set RI4 bridge port", .usage = "port" },
	{ .name = "session", .handler = ri4_handle_session, .mode = COMMAND_CONFIG,
		.help = "configure the PICkit/ICD session",
		.usage = "tool vid pid processor scripts family [tool_scripts] [suffix] [pc_bytes]" },
	{ .name = "erase", .handler = ri4_handle_erase, .mode = COMMAND_EXEC,
		.help = "erase the active target", .usage = "" },
	{ .name = "program", .handler = ri4_handle_program, .mode = COMMAND_EXEC,
		.help = "program an Intel HEX file", .usage = "path [verify]" },
	{ .name = "verify", .handler = ri4_handle_verify, .mode = COMMAND_EXEC,
		.help = "verify an Intel HEX file", .usage = "path" },
	COMMAND_REGISTRATION_DONE
};

static const struct command_registration ri4_commands[] = {
	{ .name = "mchp_ri4", .mode = COMMAND_ANY, .help = "Microchip RI4 bridge commands",
		.usage = "", .chain = ri4_subcommands },
	COMMAND_REGISTRATION_DONE
};

struct target_type mchp_ri4_bridge_target = {
	.name = "mchp_ri4_bridge",
	.commands = ri4_commands,
	.target_create = ri4_target_create,
	.init_target = ri4_init_target,
	.deinit_target = ri4_deinit_target,
	.examine = ri4_examine,
	.poll = ri4_poll,
	.halt = ri4_halt,
	.resume = ri4_resume,
	.step = ri4_step,
	.read_memory = ri4_read_memory,
	.write_memory = ri4_write_memory,
	.add_breakpoint = ri4_add_breakpoint,
	.remove_breakpoint = ri4_remove_breakpoint,
	.add_watchpoint = ri4_add_watchpoint,
	.remove_watchpoint = ri4_remove_watchpoint,
};
