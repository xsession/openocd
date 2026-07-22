// SPDX-License-Identifier: GPL-2.0-or-later

#ifdef HAVE_CONFIG_H
#include "config.h"
#endif

#include "avr_catalog.h"
#include "programmers/usbasp.h"

#include <helper/command.h>
#include <helper/log.h>

#include <ctype.h>
#include <string.h>

struct avr_backend_family {
	const char *name;
	const char *status;
	const char *sources;
	const char *scope;
	const char *next_step;
};

static const struct avr_backend_family avr_backend_families[] = {
	{
		.name = "stk500",
		.status = "staged",
		.sources = "stk500.c, stk500generic.c, arduino.c, wiring.c",
		.scope = "ISP and serial bootloader programming",
		.next_step = "add OpenOCD serial lifecycle glue and AVR memory-operation adapter",
	},
	{
		.name = "stk500v2",
		.status = "staged",
		.sources = "stk500v2.c",
		.scope = "STK500v2 and related ISP/JTAG programmer protocol",
		.next_step = "split transport framing from AVRDUDE global configuration state",
	},
	{
		.name = "serialupdi",
		.status = "staged",
		.sources = "serialupdi.c, updi_*.c",
		.scope = "AVR UPDI programming over serial adapters",
		.next_step = "map UPDI transactions onto OpenOCD target/programming commands",
	},
	{
		.name = "usbasp",
		.status = avr_usbasp_backend_status,
		.sources = "usbasp.c, usb_libusb.c",
		.scope = "USBasp ISP programmer",
		.next_step = "add typed flash, EEPROM, fuse, and lock-bit operations on top of native ISP transport",
	},
	{
		.name = "usbtiny",
		.status = "staged",
		.sources = "usbtiny.c, usb_libusb.c",
		.scope = "USBtiny ISP programmer",
		.next_step = "reuse OpenOCD libusb helpers and add typed memory operations",
	},
	{
		.name = "jtagice",
		.status = "staged",
		.sources = "jtagmkI.c, jtagmkII.c, jtag3.c",
		.scope = "AVR JTAG/debug-capable programmers",
		.next_step = "separate flash programming support from debug target support",
	},
	{
		.name = "debugwire",
		.status = "staged",
		.sources = "jtagmkII.c, jtag3.c",
		.scope = "AVR debugWIRE programming and debug entry paths",
		.next_step = "define OpenOCD target model and safe fuse handling",
	},
	{
		.name = "avrftdi",
		.status = "staged",
		.sources = "avrftdi.c, avrftdi_tpi.c, ft245r.c",
		.scope = "FTDI-backed AVR bitbang/JTAG/TPI programming",
		.next_step = "map pins and bitbang clocks onto OpenOCD adapter abstractions",
	},
	{
		.name = "linuxgpio",
		.status = "staged",
		.sources = "linuxgpio.c",
		.scope = "Linux GPIO bitbang programming",
		.next_step = "adapt host-only GPIO access behind OpenOCD platform guards",
	},
	{
		.name = "linuxspi",
		.status = "staged",
		.sources = "linuxspi.c",
		.scope = "Linux spidev ISP programming",
		.next_step = "adapt spidev access behind OpenOCD platform guards",
	},
};

static const size_t avr_backend_family_count =
	sizeof(avr_backend_families) / sizeof(avr_backend_families[0]);

static bool avr_catalog_matches(const char *filter, const char *value)
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

static bool avr_catalog_mcu_matches(const struct avr_catalog_mcu *mcu,
	const char *filter)
{
	return avr_catalog_matches(filter, mcu->id) ||
		avr_catalog_matches(filter, mcu->aliases) ||
		avr_catalog_matches(filter, mcu->description) ||
		avr_catalog_matches(filter, mcu->signature) ||
		avr_catalog_matches(filter, mcu->interfaces) ||
		avr_catalog_matches(filter, mcu->memories);
}

static bool avr_catalog_programmer_matches(
	const struct avr_catalog_programmer *programmer, const char *filter)
{
	return avr_catalog_matches(filter, programmer->id) ||
		avr_catalog_matches(filter, programmer->aliases) ||
		avr_catalog_matches(filter, programmer->description) ||
		avr_catalog_matches(filter, programmer->type) ||
		avr_catalog_matches(filter, programmer->prog_modes) ||
		avr_catalog_matches(filter, programmer->connection_type) ||
		avr_catalog_matches(filter, programmer->usbvid) ||
		avr_catalog_matches(filter, programmer->usbpid);
}

static const struct avr_backend_family *avr_backend_find_family(const char *name)
{
	for (size_t i = 0; i < avr_backend_family_count; i++) {
		const struct avr_backend_family *family = &avr_backend_families[i];
		if (avr_catalog_matches(name, family->name))
			return family;
	}

	return NULL;
}

COMMAND_HANDLER(handle_mcu_catalog_summary_command)
{
	if (CMD_ARGC != 0)
		return ERROR_COMMAND_SYNTAX_ERROR;

	command_print(CMD, "MCU catalog source: %s", avr_catalog_source);
	command_print(CMD, "MCU catalog sha256: %s", avr_catalog_source_sha256);
	command_print(CMD, "MCUs: %zu", avr_catalog_mcu_count);

	return ERROR_OK;
}

COMMAND_HANDLER(handle_mcu_catalog_list_command)
{
	if (CMD_ARGC > 1)
		return ERROR_COMMAND_SYNTAX_ERROR;

	const char *filter = CMD_ARGC == 1 ? CMD_ARGV[0] : "";
	for (size_t i = 0; i < avr_catalog_mcu_count; i++) {
		const struct avr_catalog_mcu *mcu = &avr_catalog_mcus[i];
		if (!avr_catalog_mcu_matches(mcu, filter))
			continue;

		command_print(CMD, "%s%s%s%s%s%s%s",
			mcu->id,
			mcu->description && *mcu->description ? " - " : "",
			mcu->description && *mcu->description ? mcu->description : "",
			mcu->signature && *mcu->signature ? " signature=" : "",
			mcu->signature && *mcu->signature ? mcu->signature : "",
			mcu->interfaces && *mcu->interfaces ? " interfaces=" : "",
			mcu->interfaces && *mcu->interfaces ? mcu->interfaces : "");
	}

	return ERROR_OK;
}

COMMAND_HANDLER(handle_programmer_catalog_summary_command)
{
	if (CMD_ARGC != 0)
		return ERROR_COMMAND_SYNTAX_ERROR;

	command_print(CMD, "Programmer catalog source: %s", avr_catalog_source);
	command_print(CMD, "Programmer catalog sha256: %s", avr_catalog_source_sha256);
	command_print(CMD, "Programmers: %zu", avr_catalog_programmer_count);

	return ERROR_OK;
}

COMMAND_HANDLER(handle_programmer_catalog_list_command)
{
	if (CMD_ARGC > 1)
		return ERROR_COMMAND_SYNTAX_ERROR;

	const char *filter = CMD_ARGC == 1 ? CMD_ARGV[0] : "";
	for (size_t i = 0; i < avr_catalog_programmer_count; i++) {
		const struct avr_catalog_programmer *programmer =
			&avr_catalog_programmers[i];
		if (!avr_catalog_programmer_matches(programmer, filter))
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

COMMAND_HANDLER(handle_avr_backend_status_command)
{
	if (CMD_ARGC != 0)
		return ERROR_COMMAND_SYNTAX_ERROR;

	command_print(CMD, "AVR backend source: imported");
	command_print(CMD, "AVR backend source path: src/avr/backends/avrdude");
	command_print(CMD, "AVR catalog: native compiled data");
	command_print(CMD, "AVR backend compile status: staged for protocol-family ports");
	command_print(CMD, "AVR backend families: %zu", avr_backend_family_count);

	return ERROR_OK;
}

COMMAND_HANDLER(handle_avr_backend_list_command)
{
	if (CMD_ARGC > 1)
		return ERROR_COMMAND_SYNTAX_ERROR;

	const char *filter = CMD_ARGC == 1 ? CMD_ARGV[0] : "";
	for (size_t i = 0; i < avr_backend_family_count; i++) {
		const struct avr_backend_family *family = &avr_backend_families[i];
		if (!avr_catalog_matches(filter, family->name) &&
			!avr_catalog_matches(filter, family->sources) &&
			!avr_catalog_matches(filter, family->scope))
			continue;

		command_print(CMD, "%s status=%s scope=\"%s\" sources=\"%s\"",
			family->name, family->status, family->scope, family->sources);
	}

	return ERROR_OK;
}

COMMAND_HANDLER(handle_avr_backend_show_command)
{
	if (CMD_ARGC != 1)
		return ERROR_COMMAND_SYNTAX_ERROR;

	const struct avr_backend_family *family = avr_backend_find_family(CMD_ARGV[0]);
	if (!family) {
		command_print(CMD, "AVR backend family not found: %s", CMD_ARGV[0]);
		return ERROR_FAIL;
	}

	command_print(CMD, "family: %s", family->name);
	command_print(CMD, "status: %s", family->status);
	command_print(CMD, "scope: %s", family->scope);
	command_print(CMD, "sources: %s", family->sources);
	command_print(CMD, "next step: %s", family->next_step);

	return ERROR_OK;
}

static const struct command_registration avr_backend_family_command_handlers[] = {
	{
		.name = "list",
		.handler = handle_avr_backend_list_command,
		.mode = COMMAND_ANY,
		.help = "list imported AVR backend protocol families",
		.usage = "[filter]",
	},
	{
		.name = "show",
		.handler = handle_avr_backend_show_command,
		.mode = COMMAND_ANY,
		.help = "show one imported AVR backend protocol family",
		.usage = "family",
	},
	COMMAND_REGISTRATION_DONE
};

static const struct command_registration avr_backend_command_handlers[] = {
	{
		.name = "status",
		.handler = handle_avr_backend_status_command,
		.mode = COMMAND_ANY,
		.help = "show native AVR backend port status",
		.usage = "",
	},
	{
		.name = "backend",
		.mode = COMMAND_ANY,
		.help = "native AVR backend family registry",
		.usage = "",
		.chain = avr_backend_family_command_handlers,
	},
	COMMAND_REGISTRATION_DONE
};

static const struct command_registration mcu_command_handlers[] = {
	{
		.name = "summary",
		.handler = handle_mcu_catalog_summary_command,
		.mode = COMMAND_ANY,
		.help = "show native MCU catalog source and entry count",
		.usage = "",
	},
	{
		.name = "list",
		.handler = handle_mcu_catalog_list_command,
		.mode = COMMAND_ANY,
		.help = "list native MCU catalog entries",
		.usage = "[filter]",
	},
	COMMAND_REGISTRATION_DONE
};

static const struct command_registration programmer_command_handlers[] = {
	{
		.name = "summary",
		.handler = handle_programmer_catalog_summary_command,
		.mode = COMMAND_ANY,
		.help = "show native programmer catalog source and entry count",
		.usage = "",
	},
	{
		.name = "list",
		.handler = handle_programmer_catalog_list_command,
		.mode = COMMAND_ANY,
		.help = "list native programmer catalog entries",
		.usage = "[filter]",
	},
	COMMAND_REGISTRATION_DONE
};

static const struct command_registration native_catalog_commands[] = {
	{
		.name = "mcu",
		.mode = COMMAND_ANY,
		.help = "native MCU catalog",
		.usage = "",
		.chain = mcu_command_handlers,
	},
	{
		.name = "programmer",
		.mode = COMMAND_ANY,
		.help = "native programmer catalog",
		.usage = "",
		.chain = programmer_command_handlers,
	},
	{
		.name = "avr",
		.mode = COMMAND_ANY,
		.help = "native AVR programming environment",
		.usage = "",
		.chain = avr_backend_command_handlers,
	},
	COMMAND_REGISTRATION_DONE
};

int avr_catalog_register_commands(struct command_context *cmd_ctx)
{
	return register_commands(cmd_ctx, NULL, native_catalog_commands);
}
