// SPDX-License-Identifier: GPL-2.0-or-later
/* Microchip PICkit 4 / ICD 4 native RI4 target. */

#ifdef HAVE_CONFIG_H
#include "config.h"
#endif

#include "target.h"
#include "target_type.h"
#include "register.h"
#include "breakpoints.h"
#include "image.h"
#include "mchp_ri4_bridge.h"
#include "mchp_ri4_native.h"

#include <helper/binarybuffer.h>
#include <helper/command.h>
#include <helper/log.h>
#include <helper/replacements.h>

#include <errno.h>
#include <inttypes.h>
#include <stdlib.h>
#include <string.h>

#define MCHP_RI4_TARGET_NAME "mchp_ri4_bridge"
#define MCHP_RI4_IMAGE_CHUNK 4096U

struct mchp_ri4_bridge {
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
	struct mchp_ri4_native *native;
	struct mchp_ri4_native_caps caps;
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

static int mchp_ri4_get_pc_value(struct target *target, uint32_t *pc);
static int mchp_ri4_set_pc_value(struct target *target, uint32_t pc);

bool mchp_ri4_bridge_is_target(const struct target *target)
{
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
	*value = parsed;
	return ERROR_OK;
}

static int mchp_ri4_start_session(struct mchp_ri4_bridge *bridge)
{
	if (bridge->native)
		return ERROR_OK;
	struct mchp_ri4_native_config config = {
		.vid = bridge->vid,
		.pid = bridge->pid,
		.serial = bridge->serial_number,
		.processor = bridge->processor,
		.family = bridge->family,
		.scripts_path = bridge->scripts_path,
		.tool_scripts_path = bridge->tool_scripts_path,
		.script_suffix = bridge->script_suffix,
	};
	int result = mchp_ri4_native_open(&bridge->native, &config);
	if (result == ERROR_OK)
		mchp_ri4_native_get_caps(bridge->native, &bridge->caps);
	return result;
}

static int mchp_ri4_poll(struct target *target)
{
	struct mchp_ri4_bridge *bridge = target_to_mchp_ri4(target);
	if (!bridge->native || !bridge->caps.poll)
		return ERROR_TARGET_RESOURCE_NOT_AVAILABLE;
	bool halted = false;
	int result = mchp_ri4_native_is_halted(bridge->native, &halted);
	if (result != ERROR_OK)
		return result;
	enum target_state previous = target->state;
	target->state = halted ? TARGET_HALTED : TARGET_RUNNING;
	if (previous != target->state) {
		if (target->state == TARGET_HALTED) {
			target->debug_reason = DBG_REASON_DBGRQ;
			target_call_event_callbacks(target, TARGET_EVENT_HALTED);
		} else {
			target_call_event_callbacks(target, TARGET_EVENT_RESUMED);
		}
	}
	return ERROR_OK;
}

static int mchp_ri4_halt(struct target *target)
{
	struct mchp_ri4_bridge *bridge = target_to_mchp_ri4(target);
	if (target->state == TARGET_HALTED)
		return ERROR_OK;
	int result = mchp_ri4_native_halt(bridge->native);
	if (result == ERROR_OK) {
		target->state = TARGET_HALTED;
		target->debug_reason = DBG_REASON_DBGRQ;
		target_call_event_callbacks(target, TARGET_EVENT_HALTED);
	}
	return result;
}

static int mchp_ri4_resume(struct target *target, bool current,
	target_addr_t address, bool handle_breakpoints, bool debug_execution)
{
	(void)handle_breakpoints;
	(void)debug_execution;
	if (!current) {
		if (address > UINT32_MAX)
			return ERROR_COMMAND_ARGUMENT_INVALID;
		int result = mchp_ri4_set_pc_value(target, address);
		if (result != ERROR_OK)
			return result;
	}
	struct mchp_ri4_bridge *bridge = target_to_mchp_ri4(target);
	int result = mchp_ri4_native_run(bridge->native);
	if (result == ERROR_OK) {
		target->state = TARGET_RUNNING;
		target->debug_reason = DBG_REASON_NOTHALTED;
		register_cache_invalidate(bridge->core_cache);
		target_call_event_callbacks(target, TARGET_EVENT_RESUMED);
	}
	return result;
}

static int mchp_ri4_step(struct target *target, bool current,
	target_addr_t address, bool handle_breakpoints)
{
	(void)handle_breakpoints;
	if (!current) {
		if (address > UINT32_MAX)
			return ERROR_COMMAND_ARGUMENT_INVALID;
		int result = mchp_ri4_set_pc_value(target, address);
		if (result != ERROR_OK)
			return result;
	}
	struct mchp_ri4_bridge *bridge = target_to_mchp_ri4(target);
	int result = mchp_ri4_native_step(bridge->native);
	if (result == ERROR_OK) {
		target->state = TARGET_HALTED;
		target->debug_reason = DBG_REASON_SINGLESTEP;
		register_cache_invalidate(bridge->core_cache);
		target_call_event_callbacks(target, TARGET_EVENT_HALTED);
	}
	return result;
}

static int mchp_ri4_assert_reset(struct target *target)
{
	struct mchp_ri4_bridge *bridge = target_to_mchp_ri4(target);
	int result = mchp_ri4_native_reset(bridge->native);
	if (result == ERROR_OK) {
		target->state = TARGET_RESET;
		register_cache_invalidate(bridge->core_cache);
	}
	return result;
}

static int mchp_ri4_deassert_reset(struct target *target)
{
	return target->reset_halt ? mchp_ri4_halt(target) :
		mchp_ri4_resume(target, true, 0, false, false);
}

static int mchp_ri4_soft_reset_halt(struct target *target)
{
	int result = mchp_ri4_assert_reset(target);
	return result == ERROR_OK ? mchp_ri4_halt(target) : result;
}

static int mchp_ri4_get_pc_value(struct target *target, uint32_t *pc_out)
{
	struct mchp_ri4_bridge *bridge = target_to_mchp_ri4(target);
	uint32_t pc = 0;
	int result = mchp_ri4_native_get_pc(bridge->native, bridge->pc_bytes, &pc);
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
	if (!bridge->caps.set_pc)
		return ERROR_TARGET_RESOURCE_NOT_AVAILABLE;
	int result = mchp_ri4_native_set_pc(bridge->native, pc);
	if (result == ERROR_OK) {
		buf_set_u32(bridge->pc_value, 0, bridge->pc_reg->size, pc);
		bridge->pc_reg->valid = true;
		bridge->pc_reg->dirty = false;
	}
	return result;
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
	return mchp_ri4_set_pc_value(arch_reg->target,
		buf_get_u32(buffer, 0, reg->size));
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
	struct reg **reg_list[], int *reg_list_size, enum target_register_class reg_class)
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
	if (!size || count > UINT32_MAX / size || address > UINT32_MAX)
		return ERROR_COMMAND_ARGUMENT_INVALID;
	return mchp_ri4_native_read(bridge->native, address, buffer, size * count);
}

static int mchp_ri4_write_memory(struct target *target, target_addr_t address,
	uint32_t size, uint32_t count, const uint8_t *buffer)
{
	struct mchp_ri4_bridge *bridge = target_to_mchp_ri4(target);
	if (!bridge->caps.memory_write)
		return ERROR_TARGET_RESOURCE_NOT_AVAILABLE;
	if (!size || count > UINT32_MAX / size || address > UINT32_MAX)
		return ERROR_COMMAND_ARGUMENT_INVALID;
	return mchp_ri4_native_write(bridge->native, address, buffer, size * count);
}

static int mchp_ri4_add_breakpoint(struct target *target, struct breakpoint *breakpoint)
{
	struct mchp_ri4_bridge *bridge = target_to_mchp_ri4(target);
	if (!bridge->caps.breakpoints || breakpoint->type != BKPT_HARD ||
			breakpoint->address > UINT32_MAX)
		return ERROR_TARGET_RESOURCE_NOT_AVAILABLE;
	int result = mchp_ri4_native_set_breakpoint(bridge->native,
		breakpoint->unique_id % 8U, breakpoint->address);
	if (result == ERROR_OK)
		breakpoint_hw_set(breakpoint, breakpoint->unique_id % 8U);
	return result;
}

static int mchp_ri4_remove_breakpoint(struct target *target, struct breakpoint *breakpoint)
{
	if (!breakpoint->is_set)
		return ERROR_OK;
	int result = mchp_ri4_native_clear_point(target_to_mchp_ri4(target)->native,
		breakpoint->number);
	if (result == ERROR_OK)
		breakpoint->is_set = false;
	return result;
}

static int mchp_ri4_add_watchpoint(struct target *target, struct watchpoint *watchpoint)
{
	struct mchp_ri4_bridge *bridge = target_to_mchp_ri4(target);
	if (!bridge->caps.watchpoints || watchpoint->address > UINT32_MAX)
		return ERROR_TARGET_RESOURCE_NOT_AVAILABLE;
	unsigned int access = watchpoint->rw == WPT_READ ? 1U :
		watchpoint->rw == WPT_WRITE ? 2U : 3U;
	unsigned int slot = watchpoint->unique_id % 8U;
	int result = mchp_ri4_native_set_watchpoint(bridge->native, access, slot,
		watchpoint->address);
	if (result == ERROR_OK)
		watchpoint_set(watchpoint, slot);
	return result;
}

static int mchp_ri4_remove_watchpoint(struct target *target, struct watchpoint *watchpoint)
{
	if (!watchpoint->is_set)
		return ERROR_OK;
	int result = mchp_ri4_native_clear_point(target_to_mchp_ri4(target)->native,
		watchpoint->number);
	if (result == ERROR_OK)
		watchpoint->is_set = false;
	return result;
}

static int mchp_ri4_target_create(struct target *target)
{
	struct mchp_ri4_bridge *bridge = calloc(1, sizeof(*bridge));
	if (!bridge)
		return ERROR_FAIL;
	bridge->tool = strdup("pk4");
	bridge->family = strdup("");
	bridge->processor = strdup("");
	bridge->scripts_path = strdup("");
	bridge->tool_scripts_path = strdup("");
	bridge->script_suffix = strdup("");
	bridge->serial_number = strdup("");
	bridge->vid = 0x04d8;
	bridge->pid = 0x9012;
	bridge->pc_bytes = 4;
	if (!bridge->tool || !bridge->family || !bridge->processor ||
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
	if (!bridge->caps.debug) {
		LOG_ERROR("mchp_ri4: selected catalog does not expose complete debug controls");
		return ERROR_TARGET_RESOURCE_NOT_AVAILABLE;
	}
	result = mchp_ri4_native_enter_debug(bridge->native);
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
	mchp_ri4_native_close(bridge->native);
	if (bridge->pc_reg)
		free(bridge->pc_reg->arch_info);
	free(bridge->pc_value);
	free(bridge->pc_reg);
	free(bridge->core_cache);
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
	if (!mchp_ri4_bridge_is_target(target))
		return ERROR_COMMAND_ARGUMENT_INVALID;
	struct mchp_ri4_bridge *bridge = target_to_mchp_ri4(target);
	for (unsigned int i = 1; i < CMD_ARGC; i++) {
		if (i + 1 >= CMD_ARGC)
			return ERROR_COMMAND_SYNTAX_ERROR;
		const char *option = CMD_ARGV[i];
		const char *value = CMD_ARGV[++i];
		uint32_t number = 0;
		if (strcmp(option, "-tool") == 0)
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
			if (mchp_ri4_parse_u32(value, &number) != ERROR_OK || !number || number > 4)
				return ERROR_COMMAND_ARGUMENT_INVALID;
			bridge->pc_bytes = number;
		} else {
			command_print(CMD, "unknown mchp_ri4 configure option: %s", option);
			return ERROR_COMMAND_ARGUMENT_INVALID;
		}
	}
	return ERROR_OK;
}

COMMAND_HANDLER(mchp_ri4_handle_capabilities)
{
	if (CMD_ARGC != 1)
		return ERROR_COMMAND_SYNTAX_ERROR;
	struct target *target = get_target(CMD_ARGV[0]);
	if (!mchp_ri4_bridge_is_target(target))
		return ERROR_COMMAND_ARGUMENT_INVALID;
	struct mchp_ri4_bridge *bridge = target_to_mchp_ri4(target);
	if (!bridge->native)
		return ERROR_TARGET_NOT_EXAMINED;
	command_print(CMD,
		"native_usb=1 erase=%d debug=%d poll=%d set_pc=%d breakpoints=%d watchpoints=%d memory_read=%d memory_write=%d",
		bridge->caps.erase, bridge->caps.debug, bridge->caps.poll,
		bridge->caps.set_pc, bridge->caps.breakpoints, bridge->caps.watchpoints,
		bridge->caps.memory_read, bridge->caps.memory_write);
	return ERROR_OK;
}

int mchp_ri4_bridge_mass_erase(struct target *target, unsigned int mode)
{
	if (!mchp_ri4_bridge_is_target(target))
		return ERROR_COMMAND_ARGUMENT_INVALID;
	struct mchp_ri4_bridge *bridge = target_to_mchp_ri4(target);
	if (!bridge || !bridge->native || !bridge->caps.erase)
		return ERROR_TARGET_RESOURCE_NOT_AVAILABLE;
	return mchp_ri4_native_erase(bridge->native, mode);
}

COMMAND_HANDLER(mchp_ri4_handle_erase)
{
	if (CMD_ARGC < 1 || CMD_ARGC > 2)
		return ERROR_COMMAND_SYNTAX_ERROR;
	struct target *target = get_target(CMD_ARGV[0]);
	uint32_t mode = 0;
	if (!mchp_ri4_bridge_is_target(target) ||
			(CMD_ARGC == 2 && mchp_ri4_parse_u32(CMD_ARGV[1], &mode) != ERROR_OK))
		return ERROR_COMMAND_ARGUMENT_INVALID;
	return mchp_ri4_bridge_mass_erase(target, mode);
}

static int mchp_ri4_image(struct target *target, const char *path,
	bool program, bool verify)
{
	struct image image;
	memset(&image, 0, sizeof(image));
	int result = image_open(&image, path, NULL);
	if (result != ERROR_OK)
		return result;
	if (program) {
		result = mchp_ri4_bridge_mass_erase(target, 0);
		if (result != ERROR_OK)
			goto done;
	}
	uint8_t *buffer = malloc(MCHP_RI4_IMAGE_CHUNK);
	uint8_t *actual = verify ? malloc(MCHP_RI4_IMAGE_CHUNK) : NULL;
	if (!buffer || (verify && !actual)) {
		result = ERROR_FAIL;
		goto free_buffers;
	}
	for (unsigned int section = 0; section < image.num_sections && result == ERROR_OK; section++) {
		for (uint32_t offset = 0; offset < image.sections[section].size;) {
			uint32_t length = MIN(MCHP_RI4_IMAGE_CHUNK,
				image.sections[section].size - offset);
			size_t got = 0;
			result = image_read_section(&image, section, offset, length, buffer, &got);
			if (result != ERROR_OK || got != length) {
				result = ERROR_FAIL;
				break;
			}
			target_addr_t address = image.sections[section].base_address + offset;
			if (address > UINT32_MAX) {
				result = ERROR_COMMAND_ARGUMENT_INVALID;
				break;
			}
			if (program)
				result = mchp_ri4_write_memory(target, address, 1, length, buffer);
			if (result == ERROR_OK && verify) {
				result = mchp_ri4_read_memory(target, address, 1, length, actual);
				if (result == ERROR_OK && memcmp(buffer, actual, length) != 0) {
					LOG_ERROR("mchp_ri4: verify failed at 0x%08" PRIx32,
						(uint32_t)address);
					result = ERROR_FAIL;
				}
			}
			offset += length;
		}
	}
free_buffers:
	free(actual);
	free(buffer);
done:
	image_close(&image);
	return result;
}

COMMAND_HANDLER(mchp_ri4_handle_program)
{
	if (CMD_ARGC < 2 || CMD_ARGC > 3)
		return ERROR_COMMAND_SYNTAX_ERROR;
	struct target *target = get_target(CMD_ARGV[0]);
	bool verify = CMD_ARGC == 3 && strcmp(CMD_ARGV[2], "verify") == 0;
	if (!mchp_ri4_bridge_is_target(target) || (CMD_ARGC == 3 && !verify))
		return ERROR_COMMAND_ARGUMENT_INVALID;
	return mchp_ri4_image(target, CMD_ARGV[1], true, verify);
}

COMMAND_HANDLER(mchp_ri4_handle_verify)
{
	if (CMD_ARGC != 2)
		return ERROR_COMMAND_SYNTAX_ERROR;
	struct target *target = get_target(CMD_ARGV[0]);
	if (!mchp_ri4_bridge_is_target(target))
		return ERROR_COMMAND_ARGUMENT_INVALID;
	return mchp_ri4_image(target, CMD_ARGV[1], false, true);
}

static const struct command_registration mchp_ri4_exec_command_handlers[] = {
	{
		.name = "configure",
		.handler = mchp_ri4_handle_configure,
		.mode = COMMAND_CONFIG,
		.help = "configure a native Microchip RI4 target",
		.usage = "target [-tool pk4|icd4] [-vid id] [-pid id] [-family name] "
			"-processor name -scripts path [-tool-scripts path] [-script-suffix suffix] "
			"[-serial serial] [-pc-bytes 1..4]",
	},
	{
		.name = "capabilities",
		.handler = mchp_ri4_handle_capabilities,
		.mode = COMMAND_EXEC,
		.help = "show native RI4 capabilities from the active script catalog",
		.usage = "target",
	},
	{
		.name = "erase",
		.handler = mchp_ri4_handle_erase,
		.mode = COMMAND_EXEC,
		.help = "erase the selected target through native RI4 USB",
		.usage = "target [mode]",
	},
	{
		.name = "program",
		.handler = mchp_ri4_handle_program,
		.mode = COMMAND_EXEC,
		.help = "program an image through native RI4 USB",
		.usage = "target image [verify]",
	},
	{
		.name = "verify",
		.handler = mchp_ri4_handle_verify,
		.mode = COMMAND_EXEC,
		.help = "verify an image through native RI4 USB",
		.usage = "target image",
	},
	COMMAND_REGISTRATION_DONE
};

static const struct command_registration mchp_ri4_command_handlers[] = {
	{
		.name = "mchp_ri4",
		.mode = COMMAND_ANY,
		.help = "native Microchip PICkit 4 / ICD 4 RI4 commands",
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
