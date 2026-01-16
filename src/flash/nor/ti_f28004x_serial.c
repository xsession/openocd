// SPDX-License-Identifier: GPL-2.0-or-later

#ifdef HAVE_CONFIG_H
#include "config.h"
#endif

#include "imp.h"

#include <ctype.h>
#include <stdlib.h>
#include <string.h>

#include <helper/fileio.h>

extern const struct flash_driver ti_f28004x_serial_flash;

struct ti_f28004x_serial_bank {
	char *com_port;
	int baud;
	char *device;
	char *programmer_exe;
	char *kernel_file;
};

static void ti_f28004x_serial_free(struct flash_bank *bank)
{
	if (!bank || !bank->driver_priv)
		return;

	struct ti_f28004x_serial_bank *info = bank->driver_priv;
	free(info->com_port);
	free(info->device);
	free(info->programmer_exe);
	free(info->kernel_file);
	free(info);
	bank->driver_priv = NULL;
}

static bool ti_is_com_port(const char *s)
{
	if (!s)
		return false;
	if (strlen(s) < 4)
		return false;
	if (toupper((unsigned char)s[0]) != 'C' ||
		toupper((unsigned char)s[1]) != 'O' ||
		toupper((unsigned char)s[2]) != 'M')
		return false;
	for (size_t i = 3; s[i]; i++) {
		if (!isdigit((unsigned char)s[i]))
			return false;
	}
	return true;
}

static int ti_check_readable_file(const char *path)
{
	struct fileio *fileio = NULL;
	int retval = fileio_open(&fileio, path, FILEIO_READ, FILEIO_BINARY);
	if (retval != ERROR_OK)
		return retval;
	fileio_close(fileio);
	return ERROR_OK;
}

FLASH_BANK_COMMAND_HANDLER(ti_f28004x_serial_flash_bank_command)
{
	if (CMD_ARGC < 7)
		return ERROR_COMMAND_SYNTAX_ERROR;

	struct ti_f28004x_serial_bank *info = calloc(1, sizeof(*info));
	if (!info)
		return ERROR_FAIL;

	bank->driver_priv = info;

	/* Defaults: user can override via flash bank args or via the program command */
	info->baud = 9600;
	info->device = strdup("f28004x");
	info->programmer_exe = strdup("serial_flash_programmer.exe");
	info->kernel_file = NULL;

	if (!info->device || !info->programmer_exe) {
		ti_f28004x_serial_free(bank);
		return ERROR_FAIL;
	}

	/* Driver-specific args start at CMD_ARGV[6] */
	info->com_port = strdup(CMD_ARGV[6]);
	if (!info->com_port) {
		ti_f28004x_serial_free(bank);
		return ERROR_FAIL;
	}

	if (!ti_is_com_port(info->com_port)) {
		LOG_ERROR("ti_f28004x_serial: ComPort must look like COM7, got: '%s'", info->com_port);
		ti_f28004x_serial_free(bank);
		return ERROR_COMMAND_SYNTAX_ERROR;
	}

	unsigned int index = 7;
	if (index < CMD_ARGC) {
		uint32_t temp;
		COMMAND_PARSE_NUMBER(u32, CMD_ARGV[index], temp);
		info->baud = (int)temp;
		index++;
	}
	if (index < CMD_ARGC) {
		free(info->device);
		info->device = strdup(CMD_ARGV[index++]);
		if (!info->device) {
			ti_f28004x_serial_free(bank);
			return ERROR_FAIL;
		}
	}
	if (index < CMD_ARGC) {
		free(info->programmer_exe);
		info->programmer_exe = strdup(CMD_ARGV[index++]);
		if (!info->programmer_exe) {
			ti_f28004x_serial_free(bank);
			return ERROR_FAIL;
		}
	}
	if (index < CMD_ARGC) {
		info->kernel_file = strdup(CMD_ARGV[index++]);
		if (!info->kernel_file) {
			ti_f28004x_serial_free(bank);
			return ERROR_FAIL;
		}
	}

	return ERROR_OK;
}

static int ti_f28004x_serial_probe(struct flash_bank *bank)
{
	/* This backend doesn't probe target flash; we only provide a programming hook.
	 * Provide a single pseudo-sector so flash info output is usable.
	 */
	if (bank->num_sectors && bank->sectors)
		return ERROR_OK;

	bank->num_sectors = 1;
	bank->sectors = calloc(1, sizeof(struct flash_sector));
	if (!bank->sectors) {
		bank->num_sectors = 0;
		return ERROR_FAIL;
	}

	bank->sectors[0].offset = 0;
	bank->sectors[0].size = bank->size;
	bank->sectors[0].is_erased = -1;
	bank->sectors[0].is_protected = -1;
	return ERROR_OK;
}

static int ti_f28004x_serial_auto_probe(struct flash_bank *bank)
{
	return ti_f28004x_serial_probe(bank);
}

static int ti_f28004x_serial_erase(struct flash_bank *bank, unsigned int first, unsigned int last)
{
	(void)bank;
	(void)first;
	(void)last;
	LOG_ERROR("ti_f28004x_serial: erase is not supported; use 'ti_f28004x_serial program' which performs erase as required.");
	return ERROR_FLASH_OPER_UNSUPPORTED;
}

static int ti_f28004x_serial_write(struct flash_bank *bank, const uint8_t *buffer, uint32_t offset, uint32_t count)
{
	(void)bank;
	(void)buffer;
	(void)offset;
	(void)count;
	LOG_ERROR("ti_f28004x_serial: generic flash write is not supported (TI tool requires SCI boot .txt image). Use 'ti_f28004x_serial program'.");
	return ERROR_FLASH_OPER_UNSUPPORTED;
}

static int ti_f28004x_serial_info(struct flash_bank *bank, struct command_invocation *cmd)
{
	struct ti_f28004x_serial_bank *info = bank->driver_priv;
	command_print_sameline(cmd, "ti_f28004x_serial (external TI serial_flash_programmer) port=%s baud=%d device=%s",
		info ? info->com_port : "(unset)",
		info ? info->baud : 0,
		info ? info->device : "(unset)");
	return ERROR_OK;
}

COMMAND_HANDLER(ti_f28004x_serial_handle_program)
{
	struct flash_bank *bank = NULL;
	int retval = CALL_COMMAND_HANDLER(flash_command_get_bank_probe_optional, 0, &bank, false);
	if (retval != ERROR_OK)
		return retval;
	if (!bank || bank->driver != &ti_f28004x_serial_flash) {
		command_print(CMD, "ti_f28004x_serial: bank is not a ti_f28004x_serial bank");
		return ERROR_COMMAND_SYNTAX_ERROR;
	}

	struct ti_f28004x_serial_bank *info = bank->driver_priv;
	if (!info) {
		command_print(CMD, "ti_f28004x_serial: bank not initialized");
		return ERROR_FAIL;
	}

	if (CMD_ARGC < 2 || CMD_ARGC > 5)
		return ERROR_COMMAND_SYNTAX_ERROR;

	const char *app_file = CMD_ARGV[1];
	const char *com_port = info->com_port;
	int baud = info->baud;

	if (CMD_ARGC >= 3)
		com_port = CMD_ARGV[2];
	if (CMD_ARGC >= 4) {
		uint32_t temp;
		COMMAND_PARSE_NUMBER(u32, CMD_ARGV[3], temp);
		baud = (int)temp;
	}

	const char *kernel_file = info->kernel_file;
	if (CMD_ARGC >= 5)
		kernel_file = CMD_ARGV[4];

	if (!ti_is_com_port(com_port)) {
		command_print(CMD, "ti_f28004x_serial: ComPort must look like COM7, got: %s", com_port);
		return ERROR_COMMAND_SYNTAX_ERROR;
	}

	retval = ti_check_readable_file(app_file);
	if (retval != ERROR_OK) {
		command_print(CMD, "ti_f28004x_serial: cannot read app file: %s", app_file);
		return retval;
	}
	if (!kernel_file) {
		command_print(CMD, "ti_f28004x_serial: kernel file not set. Provide it as 5th arg or in flash bank args.");
		return ERROR_COMMAND_SYNTAX_ERROR;
	}
	retval = ti_check_readable_file(kernel_file);
	if (retval != ERROR_OK) {
		command_print(CMD, "ti_f28004x_serial: cannot read kernel file: %s", kernel_file);
		return retval;
	}

	/* If programmer_exe contains a path separator, sanity check it exists. */
	if (strchr(info->programmer_exe, '\\') || strchr(info->programmer_exe, '/')) {
		retval = ti_check_readable_file(info->programmer_exe);
		if (retval != ERROR_OK) {
			command_print(CMD, "ti_f28004x_serial: cannot access programmer exe: %s", info->programmer_exe);
			return retval;
		}
	}

	char cmdline[4096];
	int n = snprintf(cmdline, sizeof(cmdline),
		"\"%s\" -d %s -k \"%s\" -a \"%s\" -b %d -p %s",
		info->programmer_exe,
		info->device,
		kernel_file,
		app_file,
		baud,
		com_port);
	if (n < 0 || (size_t)n >= sizeof(cmdline)) {
		command_print(CMD, "ti_f28004x_serial: command line too long");
		return ERROR_FAIL;
	}

	command_print(CMD, "ti_f28004x_serial: running: %s", cmdline);
	int rc = system(cmdline);
	if (rc != 0) {
		command_print(CMD, "ti_f28004x_serial: TI programmer failed (rc=%d)", rc);
		return ERROR_FLASH_OPERATION_FAILED;
	}

	flash_set_dirty();
	return ERROR_OK;
}

static const struct command_registration ti_f28004x_serial_exec_command_handlers[] = {
	{
		.name = "program",
		.handler = ti_f28004x_serial_handle_program,
		.mode = COMMAND_EXEC,
		.usage = "bank_id app_txt [COMx] [baud] [kernel_txt]",
		.help = "Program a TI C2000 device via TI serial_flash_programmer.exe. app_txt/kernel_txt must be TI SCI boot-format text files.",
	},
	COMMAND_REGISTRATION_DONE
};

static const struct command_registration ti_f28004x_serial_command_handlers[] = {
	{
		.name = "ti_f28004x_serial",
		.mode = COMMAND_ANY,
		.help = "TI F28004x serial flash programmer command group",
		.usage = "",
		.chain = ti_f28004x_serial_exec_command_handlers,
	},
	COMMAND_REGISTRATION_DONE
};

const struct flash_driver ti_f28004x_serial_flash = {
	.name = "ti_f28004x_serial",
	.usage = "flash bank ti_f28004x_serial <base> <size> <chip_width> <bus_width> <target> <COMx> [baud] [device] [programmer_exe] [kernel_txt]",
	.commands = ti_f28004x_serial_command_handlers,
	.flash_bank_command = ti_f28004x_serial_flash_bank_command,
	.erase = ti_f28004x_serial_erase,
	.write = ti_f28004x_serial_write,
	.read = default_flash_read,
	.probe = ti_f28004x_serial_probe,
	.auto_probe = ti_f28004x_serial_auto_probe,
	.erase_check = default_flash_blank_check,
	.info = ti_f28004x_serial_info,
	.free_driver_priv = ti_f28004x_serial_free,
};
