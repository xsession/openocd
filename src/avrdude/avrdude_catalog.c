// SPDX-License-Identifier: GPL-2.0-or-later

#ifdef HAVE_CONFIG_H
#include "config.h"
#endif

#include "avrdude_catalog.h"

#include <helper/command.h>
#include <helper/log.h>

#include <ctype.h>
#include <string.h>

static bool avrdude_catalog_matches(const char *filter, const char *value)
{
	if (!filter || !*filter)
		return true;
	if (!value)
		return false;

	size_t filter_len = strlen(filter);
	for (const char *cursor = value; *cursor; cursor++) {
		size_t i;
		for (i = 0; i < filter_len; i++) {
			unsigned char value_ch = cursor[i];
			unsigned char filter_ch = filter[i];
			if (!value_ch)
				return false;
			if (tolower(value_ch) != tolower(filter_ch))
				break;
		}
		if (i == filter_len)
			return true;
	}
	return false;
}

static bool avrdude_catalog_part_matches(const struct avrdude_catalog_part *part,
	const char *filter)
{
	return avrdude_catalog_matches(filter, part->id) ||
		avrdude_catalog_matches(filter, part->aliases) ||
		avrdude_catalog_matches(filter, part->description) ||
		avrdude_catalog_matches(filter, part->signature) ||
		avrdude_catalog_matches(filter, part->interfaces) ||
		avrdude_catalog_matches(filter, part->memories);
}

static bool avrdude_catalog_programmer_matches(
	const struct avrdude_catalog_programmer *programmer, const char *filter)
{
	return avrdude_catalog_matches(filter, programmer->id) ||
		avrdude_catalog_matches(filter, programmer->aliases) ||
		avrdude_catalog_matches(filter, programmer->description) ||
		avrdude_catalog_matches(filter, programmer->type) ||
		avrdude_catalog_matches(filter, programmer->prog_modes) ||
		avrdude_catalog_matches(filter, programmer->connection_type) ||
		avrdude_catalog_matches(filter, programmer->usbvid) ||
		avrdude_catalog_matches(filter, programmer->usbpid);
}

COMMAND_HANDLER(handle_avrdude_catalog_summary_command)
{
	if (CMD_ARGC != 0)
		return ERROR_COMMAND_SYNTAX_ERROR;

	command_print(CMD, "AVRDUDE catalog source: %s", avrdude_catalog_source);
	command_print(CMD, "AVRDUDE catalog sha256: %s", avrdude_catalog_source_sha256);
	command_print(CMD, "AVRDUDE parts: %zu", avrdude_catalog_part_count);
	command_print(CMD, "AVRDUDE programmers: %zu", avrdude_catalog_programmer_count);

	return ERROR_OK;
}

COMMAND_HANDLER(handle_avrdude_catalog_parts_command)
{
	if (CMD_ARGC > 1)
		return ERROR_COMMAND_SYNTAX_ERROR;

	const char *filter = CMD_ARGC == 1 ? CMD_ARGV[0] : "";
	for (size_t i = 0; i < avrdude_catalog_part_count; i++) {
		const struct avrdude_catalog_part *part = &avrdude_catalog_parts[i];
		if (!avrdude_catalog_part_matches(part, filter))
			continue;

		command_print(CMD, "%s%s%s%s%s%s%s",
			part->id,
			part->description && *part->description ? " - " : "",
			part->description && *part->description ? part->description : "",
			part->signature && *part->signature ? " signature=" : "",
			part->signature && *part->signature ? part->signature : "",
			part->interfaces && *part->interfaces ? " interfaces=" : "",
			part->interfaces && *part->interfaces ? part->interfaces : "");
	}

	return ERROR_OK;
}

COMMAND_HANDLER(handle_avrdude_catalog_programmers_command)
{
	if (CMD_ARGC > 1)
		return ERROR_COMMAND_SYNTAX_ERROR;

	const char *filter = CMD_ARGC == 1 ? CMD_ARGV[0] : "";
	for (size_t i = 0; i < avrdude_catalog_programmer_count; i++) {
		const struct avrdude_catalog_programmer *programmer =
			&avrdude_catalog_programmers[i];
		if (!avrdude_catalog_programmer_matches(programmer, filter))
			continue;

		command_print(CMD, "%s%s%s%s%s%s%s%s%s",
			programmer->id,
			programmer->description && *programmer->description ? " - " : "",
			programmer->description && *programmer->description ?
				programmer->description : "",
			programmer->type && *programmer->type ? " type=" : "",
			programmer->type && *programmer->type ? programmer->type : "",
			programmer->prog_modes && *programmer->prog_modes ? " modes=" : "",
			programmer->prog_modes && *programmer->prog_modes ?
				programmer->prog_modes : "",
			programmer->connection_type && *programmer->connection_type ?
				" connection=" : "",
			programmer->connection_type && *programmer->connection_type ?
				programmer->connection_type : "");
	}

	return ERROR_OK;
}

static const struct command_registration avrdude_catalog_command_handlers[] = {
	{
		.name = "summary",
		.handler = handle_avrdude_catalog_summary_command,
		.mode = COMMAND_ANY,
		.help = "show generated AVRDUDE catalog source and entry counts",
		.usage = "",
	},
	{
		.name = "parts",
		.handler = handle_avrdude_catalog_parts_command,
		.mode = COMMAND_ANY,
		.help = "list AVRDUDE MCU/part catalog entries",
		.usage = "[filter]",
	},
	{
		.name = "programmers",
		.handler = handle_avrdude_catalog_programmers_command,
		.mode = COMMAND_ANY,
		.help = "list AVRDUDE programmer catalog entries",
		.usage = "[filter]",
	},
	COMMAND_REGISTRATION_DONE
};

static const struct command_registration avrdude_catalog_commands[] = {
	{
		.name = "avrdude_catalog",
		.mode = COMMAND_ANY,
		.help = "compiled AVRDUDE MCU/programmer catalog imported from avrdude.conf",
		.usage = "",
		.chain = avrdude_catalog_command_handlers,
	},
	COMMAND_REGISTRATION_DONE
};

int avrdude_catalog_register_commands(struct command_context *cmd_ctx)
{
	return register_commands(cmd_ctx, NULL, avrdude_catalog_commands);
}
