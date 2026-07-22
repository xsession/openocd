// SPDX-License-Identifier: GPL-2.0-or-later
/* Native Microchip PICkit 4 programmer commands using the RI4 USB transport. */

#ifdef HAVE_CONFIG_H
#include "config.h"
#endif

#include "pickit4.h"

#include <helper/command.h>
#include <helper/log.h>
#include <target/mchp_ri4_native.h>

#include <stdbool.h>
#include <stdint.h>
#include <string.h>

#define PICKIT4_DEFAULT_VID 0x04d8
#define PICKIT4_DEFAULT_PID 0x9012

struct pickit4_options {
	uint16_t vid;
	uint16_t pid;
	const char *serial;
	const char *processor;
	const char *family;
	const char *scripts_path;
	const char *tool_scripts_path;
	const char *script_suffix;
	unsigned int erase_mode;
};

static void pickit4_init_options(struct pickit4_options *options)
{
	memset(options, 0, sizeof(*options));
	options->vid = PICKIT4_DEFAULT_VID;
	options->pid = PICKIT4_DEFAULT_PID;
}

static int pickit4_parse_u16(const char *text, uint16_t *out)
{
	unsigned int value;
	int retval = parse_uint(text, &value);
	if (retval != ERROR_OK)
		return retval;
	if (value > UINT16_MAX)
		return ERROR_COMMAND_ARGUMENT_INVALID;
	*out = (uint16_t)value;
	return ERROR_OK;
}

static int pickit4_parse_options(unsigned int argc, const char **argv,
	struct pickit4_options *options)
{
	for (unsigned int i = 0; i < argc; i++) {
		if (i + 1 >= argc)
			return ERROR_COMMAND_SYNTAX_ERROR;
		const char *name = argv[i++];
		const char *value = argv[i];

		if (strcmp(name, "vid") == 0) {
			int retval = pickit4_parse_u16(value, &options->vid);
			if (retval != ERROR_OK)
				return retval;
		} else if (strcmp(name, "pid") == 0) {
			int retval = pickit4_parse_u16(value, &options->pid);
			if (retval != ERROR_OK)
				return retval;
		} else if (strcmp(name, "serial") == 0) {
			options->serial = value;
		} else if (strcmp(name, "processor") == 0) {
			options->processor = value;
		} else if (strcmp(name, "family") == 0) {
			options->family = value;
		} else if (strcmp(name, "scripts") == 0) {
			options->scripts_path = value;
		} else if (strcmp(name, "tool_scripts") == 0) {
			options->tool_scripts_path = value;
		} else if (strcmp(name, "suffix") == 0) {
			options->script_suffix = value;
		} else if (strcmp(name, "erase_mode") == 0) {
			int retval = parse_uint(value, &options->erase_mode);
			if (retval != ERROR_OK)
				return retval;
		} else {
			return ERROR_COMMAND_ARGUMENT_INVALID;
		}
	}

	return ERROR_OK;
}

static int pickit4_validate_session_options(struct command_invocation *cmd,
	const struct pickit4_options *options)
{
	if (!options->processor || !*options->processor) {
		command_print(cmd, "missing required option: processor <name>");
		return ERROR_COMMAND_ARGUMENT_INVALID;
	}
	if (!options->scripts_path || !*options->scripts_path) {
		command_print(cmd, "missing required option: scripts <path>");
		return ERROR_COMMAND_ARGUMENT_INVALID;
	}
	return ERROR_OK;
}

static int pickit4_open_session(struct mchp_ri4_native **session,
	const struct pickit4_options *options)
{
	struct mchp_ri4_native_config config = {
		.vid = options->vid,
		.pid = options->pid,
		.serial = options->serial,
		.processor = options->processor,
		.family = options->family,
		.scripts_path = options->scripts_path,
		.tool_scripts_path = options->tool_scripts_path,
		.script_suffix = options->script_suffix,
	};

	return mchp_ri4_native_open(session, &config);
}

COMMAND_HANDLER(handle_pickit4_status_command)
{
	if (CMD_ARGC != 0)
		return ERROR_COMMAND_SYNTAX_ERROR;

	command_print(CMD, "PICkit 4 native programmer backend: ri4-native");
	command_print(CMD, "default USB ID: %04x:%04x",
		PICKIT4_DEFAULT_VID, PICKIT4_DEFAULT_PID);
	command_print(CMD, "commands: probe, capabilities, erase");
	command_print(CMD, "external MPLAB IPECMD is not used by this command group");
	return ERROR_OK;
}

COMMAND_HANDLER(handle_pickit4_probe_command)
{
	struct pickit4_options options;
	pickit4_init_options(&options);
	int retval = pickit4_parse_options(CMD_ARGC, CMD_ARGV, &options);
	if (retval != ERROR_OK)
		return retval;

	retval = mchp_ri4_native_probe_usb(options.vid, options.pid, options.serial);
	if (retval != ERROR_OK) {
		command_print(CMD, "PICkit 4 probe: no RI4 USB device opened");
		command_print(CMD, "expected VID/PID: %04x:%04x", options.vid, options.pid);
		return retval;
	}

	command_print(CMD, "PICkit 4 probe: opened RI4 USB device %04x:%04x",
		options.vid, options.pid);
	return ERROR_OK;
}

COMMAND_HANDLER(handle_pickit4_capabilities_command)
{
	struct pickit4_options options;
	pickit4_init_options(&options);
	int retval = pickit4_parse_options(CMD_ARGC, CMD_ARGV, &options);
	if (retval != ERROR_OK)
		return retval;
	retval = pickit4_validate_session_options(CMD, &options);
	if (retval != ERROR_OK)
		return retval;

	struct mchp_ri4_native *session = NULL;
	retval = pickit4_open_session(&session, &options);
	if (retval != ERROR_OK)
		return retval;

	struct mchp_ri4_native_caps caps;
	mchp_ri4_native_get_caps(session, &caps);

	command_print(CMD, "PICkit 4 RI4 capabilities for %s%s%s:",
		options.processor, options.family && *options.family ? " / " : "",
		options.family && *options.family ? options.family : "");
	command_print(CMD, "erase: %s", caps.erase ? "yes" : "no");
	command_print(CMD, "debug: %s", caps.debug ? "yes" : "no");
	command_print(CMD, "poll: %s", caps.poll ? "yes" : "no");
	command_print(CMD, "set_pc: %s", caps.set_pc ? "yes" : "no");
	command_print(CMD, "breakpoints: %s", caps.breakpoints ? "yes" : "no");
	command_print(CMD, "watchpoints: %s", caps.watchpoints ? "yes" : "no");
	command_print(CMD, "memory_read: %s", caps.memory_read ? "yes" : "no");
	command_print(CMD, "memory_write: %s", caps.memory_write ? "yes" : "no");

	mchp_ri4_native_close(session);
	return ERROR_OK;
}

COMMAND_HANDLER(handle_pickit4_erase_command)
{
	struct pickit4_options options;
	pickit4_init_options(&options);
	int retval = pickit4_parse_options(CMD_ARGC, CMD_ARGV, &options);
	if (retval != ERROR_OK)
		return retval;
	retval = pickit4_validate_session_options(CMD, &options);
	if (retval != ERROR_OK)
		return retval;

	struct mchp_ri4_native *session = NULL;
	retval = pickit4_open_session(&session, &options);
	if (retval != ERROR_OK)
		return retval;

	retval = mchp_ri4_native_erase(session, options.erase_mode);
	mchp_ri4_native_close(session);
	if (retval == ERROR_OK)
		command_print(CMD, "PICkit 4 erase complete");
	return retval;
}

static const struct command_registration pickit4_command_handlers[] = {
	{
		.name = "status",
		.handler = handle_pickit4_status_command,
		.mode = COMMAND_ANY,
		.help = "show native PICkit 4 backend status",
		.usage = "",
	},
	{
		.name = "probe",
		.handler = handle_pickit4_probe_command,
		.mode = COMMAND_ANY,
		.help = "open and close a PICkit 4 RI4 USB device",
		.usage = "[vid <vid>] [pid <pid>] [serial <serial>]",
	},
	{
		.name = "capabilities",
		.handler = handle_pickit4_capabilities_command,
		.mode = COMMAND_ANY,
		.help = "load RI4 scripts, open PICkit 4 and report supported native operations",
		.usage = "processor <name> scripts <path> [family <name>] "
			"[tool_scripts <path>] [suffix <suffix>] [vid <vid>] [pid <pid>] "
			"[serial <serial>]",
	},
	{
		.name = "erase",
		.handler = handle_pickit4_erase_command,
		.mode = COMMAND_ANY,
		.help = "erase a Microchip target through native PICkit 4 RI4 scripts",
		.usage = "processor <name> scripts <path> [family <name>] "
			"[tool_scripts <path>] [suffix <suffix>] [erase_mode <mode>] "
			"[vid <vid>] [pid <pid>] [serial <serial>]",
	},
	COMMAND_REGISTRATION_DONE
};

static const struct command_registration pickit4_commands[] = {
	{
		.name = "pickit4",
		.mode = COMMAND_ANY,
		.help = "native Microchip PICkit 4 programmer",
		.usage = "",
		.chain = pickit4_command_handlers,
	},
	COMMAND_REGISTRATION_DONE
};

int microchip_pickit4_register_commands(struct command_context *cmd_ctx)
{
	return register_commands(cmd_ctx, NULL, pickit4_commands);
}
