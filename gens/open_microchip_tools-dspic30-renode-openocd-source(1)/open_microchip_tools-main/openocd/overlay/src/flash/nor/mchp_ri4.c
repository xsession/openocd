// SPDX-License-Identifier: GPL-2.0-or-later
/*
 * OpenOCD NOR flash facade for the Microchip RI4 JSON bridge target.
 *
 * Device packs expose a chip erase rather than reliable, uniform sector
 * geometry across all supported PIC/dsPIC families. The bank is therefore
 * represented as one erase block. Standard OpenOCD image programming can
 * still write and verify arbitrary byte ranges through the target callbacks;
 * an erase request deliberately erases the complete configured bank.
 */
#ifdef HAVE_CONFIG_H
#include "config.h"
#endif

#include "imp.h"

#include <helper/log.h>
#include <target/mchp_ri4_bridge.h>

#include <errno.h>
#include <inttypes.h>
#include <limits.h>
#include <stdlib.h>
#include <string.h>

struct mchp_ri4_flash_bank {
	unsigned int erase_mode;
	bool probed;
};

static int mchp_ri4_parse_uint(const char *text, unsigned int *value)
{
	char *end = NULL;
	errno = 0;
	unsigned long parsed = strtoul(text, &end, 0);
	if (errno || !end || *end != '\0' || parsed > UINT_MAX)
		return ERROR_COMMAND_ARGUMENT_INVALID;
	*value = (unsigned int)parsed;
	return ERROR_OK;
}

/* flash bank <name> mchp_ri4 <base> <size> <chip_width> <bus_width>
 *            <target> [erase_mode]
 */
FLASH_BANK_COMMAND_HANDLER(mchp_ri4_flash_bank_command)
{
	if (CMD_ARGC < 6 || CMD_ARGC > 7)
		return ERROR_COMMAND_SYNTAX_ERROR;
	if (!bank->target || !mchp_ri4_bridge_is_target(bank->target)) {
		LOG_ERROR("mchp_ri4 flash bank requires an mchp_ri4_bridge target");
		return ERROR_COMMAND_ARGUMENT_INVALID;
	}
	if (bank->size == 0) {
		LOG_ERROR("mchp_ri4 flash bank size must be non-zero");
		return ERROR_COMMAND_ARGUMENT_INVALID;
	}

	struct mchp_ri4_flash_bank *info = calloc(1, sizeof(*info));
	if (!info)
		return ERROR_FAIL;
	if (CMD_ARGC == 7 && mchp_ri4_parse_uint(CMD_ARGV[6], &info->erase_mode) != ERROR_OK) {
		free(info);
		return ERROR_COMMAND_ARGUMENT_INVALID;
	}

	bank->driver_priv = info;
	bank->num_sectors = 1;
	bank->sectors = alloc_block_array(0, bank->size, 1);
	if (!bank->sectors) {
		free(info);
		bank->driver_priv = NULL;
		return ERROR_FAIL;
	}
	bank->sectors[0].is_protected = 0;
	bank->write_start_alignment = 1;
	bank->write_end_alignment = 1;
	bank->minimal_write_gap = FLASH_WRITE_CONTINUOUS;
	return ERROR_OK;
}

static int mchp_ri4_flash_probe(struct flash_bank *bank)
{
	struct mchp_ri4_flash_bank *info = bank->driver_priv;
	if (!info || !bank->target || !mchp_ri4_bridge_is_target(bank->target))
		return ERROR_FLASH_BANK_INVALID;
	info->probed = true;
	return ERROR_OK;
}

static int mchp_ri4_flash_auto_probe(struct flash_bank *bank)
{
	struct mchp_ri4_flash_bank *info = bank->driver_priv;
	if (info && info->probed)
		return ERROR_OK;
	return mchp_ri4_flash_probe(bank);
}

static int mchp_ri4_flash_erase(struct flash_bank *bank,
		unsigned int first, unsigned int last)
{
	struct mchp_ri4_flash_bank *info = bank->driver_priv;
	if (!info || first != 0 || last != 0) {
		LOG_ERROR("mchp_ri4 exposes one full-bank erase block");
		return ERROR_FLASH_SECTOR_INVALID;
	}
	return mchp_ri4_bridge_mass_erase(bank->target, info->erase_mode);
}

static int mchp_ri4_flash_write(struct flash_bank *bank,
		const uint8_t *buffer, uint32_t offset, uint32_t count)
{
	if (offset > bank->size || count > bank->size - offset)
		return ERROR_FLASH_DST_OUT_OF_BANK;
	return target_write_buffer(bank->target, bank->base + offset, count, buffer);
}

static int mchp_ri4_flash_verify(struct flash_bank *bank,
		const uint8_t *buffer, uint32_t offset, uint32_t count)
{
	if (offset > bank->size || count > bank->size - offset)
		return ERROR_FLASH_DST_OUT_OF_BANK;
	uint8_t readback[4096];
	uint32_t compared = 0;
	while (compared < count) {
		uint32_t chunk = MIN((uint32_t)sizeof(readback), count - compared);
		int result = target_read_buffer(bank->target,
			bank->base + offset + compared, chunk, readback);
		if (result != ERROR_OK)
			return result;
		if (memcmp(readback, buffer + compared, chunk) != 0) {
			LOG_ERROR("mchp_ri4 verification failed at " TARGET_ADDR_FMT,
				bank->base + offset + compared);
			return ERROR_FAIL;
		}
		compared += chunk;
	}
	return ERROR_OK;
}

static int mchp_ri4_flash_info(struct flash_bank *bank,
		struct command_invocation *cmd)
{
	struct mchp_ri4_flash_bank *info = bank->driver_priv;
	command_print_sameline(cmd,
		"Microchip RI4 bridge flash, base=" TARGET_ADDR_FMT
		", size=0x%08" PRIx32 ", erase_mode=%u, full-bank erase",
		bank->base, bank->size, info ? info->erase_mode : 0);
	return ERROR_OK;
}

const struct flash_driver mchp_ri4_flash = {
	.name = "mchp_ri4",
	.usage = "[erase_mode]",
	.flash_bank_command = mchp_ri4_flash_bank_command,
	.erase = mchp_ri4_flash_erase,
	.write = mchp_ri4_flash_write,
	.read = default_flash_read,
	.verify = mchp_ri4_flash_verify,
	.probe = mchp_ri4_flash_probe,
	.auto_probe = mchp_ri4_flash_auto_probe,
	.erase_check = default_flash_blank_check,
	.info = mchp_ri4_flash_info,
	.free_driver_priv = default_flash_free_driver_priv,
};
