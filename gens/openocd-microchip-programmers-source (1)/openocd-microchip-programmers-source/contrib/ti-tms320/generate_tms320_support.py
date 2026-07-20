#!/usr/bin/env python3
import os, re, zipfile, xml.etree.ElementTree as ET
from pathlib import Path

repo = Path('/mnt/data/openocd-tms320-work')
zip_path = Path('/mnt/data/ccs_base.zip')
z = zipfile.ZipFile(zip_path)

family_specs = {
    'c55xx': ('TMS320C55XX_regids.xml', 'c55xx.xml', 'TMS320C55XX', '0x50015400', 'tixds55x.dvr'),
    'c64xx': ('TMS320C64XX_regids.xml', 'c64xx.xml', 'TMS320C64XX', '0x500193F8', 'tixds6400_11.dvr'),
    'c64xp': ('TMS320C64XX_regids.xml', 'c64xp.xml', 'TMS320C64XP', '0x50019348', 'tixds6400_plus.dvr'),
    'c646x': ('TMS320C64XX_regids.xml', 'c646x.xml', 'TMS320C646X', '0x50019350', 'tixds6400_plus.dvr'),
    'c66xx': ('TMS320C66XX_regids.xml', 'c66xx.xml', 'TMS320C66XX', '0x50019BF8', 'tixds6400_plus.dvr'),
    'c674x': ('TMS320C674X_regids.xml', 'c674x.xml', 'TMS320C674X', '0x50019F40', 'tixds6400_plus.dvr'),
    'c6xxx': ('TMS320C6XXX_regids.xml', 'c64xx.xml', 'TMS320C6XXX', '0x50018B20', 'tixds6000.dvr'),
    'c620x': ('TMS320C6XXX_regids.xml', 'c64xx.xml', 'TMS320C620X', '0x50018B20', 'tixds6000.dvr'),
    'c621x': ('TMS320C6XXX_regids.xml', 'c64xx.xml', 'TMS320C621X', '0x50018B28', 'tixds6000.dvr'),
    'c670x': ('TMS320C6XXX_regids.xml', 'c670x.xml', 'TMS320C670X', '0x50019F20', 'tixds6000.dvr'),
    'c671x': ('TMS320C6XXX_regids.xml', 'c671x.xml', 'TMS320C671X', '0x50019F28', 'tixds6000.dvr'),
    'c672x': ('TMS320C6XXX_regids.xml', 'c672x.xml', 'TMS320C672X', '0x50019F30', 'tixds6000.dvr'),
    'c71x': ('TMS320C71XX_regids.xml', 'c71x.xml', 'TMS320C71XX', '0x5001C7F8', 'tixds510c71x.dvr'),
    'c71x_v2': ('TMS320C71XX_regids.xml', 'c71x_v2.xml', 'TMS320C71XX', '0x5001C7F8', 'tixds510c71x.dvr'),
    'c75x': ('TMS320C75XX_regids.xml', 'c75x.xml', 'TMS320C75XX', '0x5001D7F8', 'tixds510c71x.dvr'),
}

isa_to_family = {
    'TMS320C55XX': 'c55xx',
    'TMS320C64XX': 'c64xx',
    'TMS320C64XP': 'c64xp',
    'TMS320C646X': 'c646x',
    'TMS320C66XX': 'c66xx',
    'TMS320C66xx': 'c66xx',
    'TMS320C674X': 'c674x',
    'TMS320C620X': 'c620x',
    'TMS320C621X': 'c621x',
    'TMS320C670X': 'c670x',
    'TMS320C671X': 'c671x',
    'TMS320C672X': 'c672x',
    'TMS320C71XX': 'c71x',
    'TMS320C75XX': 'c75x',
}


def read_xml(name):
    return z.read(name).decode('utf-8', errors='ignore')

def parse_xml(name):
    return ET.fromstring(read_xml(name))

def sanitize_c(s):
    s = re.sub(r'[^A-Za-z0-9_]', '_', s)
    if not s or s[0].isdigit(): s = '_' + s
    return s

def q(s):
    return '"' + (s or '').replace('\\','/').replace('"','\\"') + '"'

def parse_int(s, default=0):
    if s is None or s == '': return default
    try: return int(s, 0)
    except Exception: return default

# CPU width maps
width_maps = {}
for fam, (regfile, cpufile, isa, procid, drv) in family_specs.items():
    w = {}
    path = 'ccs_base/common/targetdb/cpus/' + cpufile
    if path in z.namelist():
        try:
            root = parse_xml(path)
            for r in root.iter('register'):
                name = r.attrib.get('id') or r.attrib.get('acronym')
                width = parse_int(r.attrib.get('width'), 32)
                if name:
                    w[name.upper()] = width
                    acr = r.attrib.get('acronym')
                    if acr: w[acr.upper()] = width
        except Exception:
            pass
    width_maps[fam] = w

family_regs = {}
for fam, (regfile, cpufile, isa, procid, drv) in family_specs.items():
    path = 'ccs_base/common/targetdb/drivers/TI_reg_ids/' + regfile
    regs=[]
    root = parse_xml(path)
    seen=set()
    for r in root.iter('register_id'):
        name = r.attrib.get('id')
        if not name or name in seen: continue
        seen.add(name)
        val = parse_int(r.attrib.get('value'), -1)
        addr = parse_int(r.attrib.get('address'), 0)
        page = parse_int(r.attrib.get('page'), 0)
        width = width_maps[fam].get(name.upper(), 32)
        # sanity cap; CCS XML occasionally omits width for control aliases.
        if width <= 0 or width > 256: width = 32
        regs.append((name, val, addr, page, width))
    family_regs[fam]=regs

# Generate header and C backend
h = r'''/* SPDX-License-Identifier: GPL-2.0-or-later */

#ifndef OPENOCD_TARGET_TMS320_H
#define OPENOCD_TARGET_TMS320_H

#include "target.h"
#include "register.h"

struct tms320_family_desc;

struct tms320_reg_arch_info {
	struct tms320_common *tms320;
	unsigned int num;
	int32_t ti_id;
	uint32_t address;
	unsigned int page;
};

struct tms320_common {
	struct target *target;
	const struct tms320_family_desc *family;
	struct reg_cache *core_cache;
	uint8_t *reg_values;
	struct tms320_reg_arch_info *reg_info;
	char *device_name;
	char *core_name;
	char *gel_file;
	uint32_t procid;
	uint32_t icepick_port;
	bool icepick_port_valid;
};

#endif /* OPENOCD_TARGET_TMS320_H */
'''
(repo/'src/target/tms320.h').write_text(h)

c_parts=[]
c_parts.append(r'''// SPDX-License-Identifier: GPL-2.0-or-later

/***************************************************************************
 *   CCS-derived TI TMS320 target metadata support for OpenOCD              *
 *                                                                         *
 *   This backend covers non-C28x TMS320 DSP families by importing the      *
 *   register-ID and driver metadata present in TI Code Composer Studio's   *
 *   targetdb XML files. It intentionally fails closed for low-level        *
 *   halt/run/memory operations because those families use TI-private       *
 *   GTI/PRSC/native debug transports which are not exposed as public JTAG   *
 *   IR/DR packet specifications.                                           *
 ***************************************************************************/

#ifdef HAVE_CONFIG_H
#include "config.h"
#endif

#include <helper/binarybuffer.h>
#include <helper/command.h>
#include <helper/log.h>

#include "tms320.h"
#include "target_type.h"

struct tms320_reg_desc {
	const char *name;
	int32_t ti_id;
	uint32_t address;
	unsigned int page;
	unsigned int bits;
};

struct tms320_family_desc {
	const char *key;
	const char *isa;
	const char *gdb_arch;
	uint32_t procid;
	const char *driver;
	const struct tms320_reg_desc *regs;
	unsigned int num_regs;
};

''')
for fam, regs in family_regs.items():
    arr=f'tms320_{sanitize_c(fam)}_regs'
    c_parts.append(f'static const struct tms320_reg_desc {arr}[] = {{\n')
    for name,val,addr,page,bits in regs:
        c_parts.append(f'\t{{ {q(name)}, {val}, 0x{addr:x}u, {page}u, {bits}u }},\n')
    c_parts.append('};\n\n')

c_parts.append('static const struct tms320_family_desc tms320_families[] = {\n')
for fam,(regfile,cpufile,isa,procid,drv) in family_specs.items():
    arr=f'tms320_{sanitize_c(fam)}_regs'
    gdb = fam.replace('_','-')
    c_parts.append(f'\t{{ {q(fam)}, {q(isa)}, {q(gdb)}, {procid}u, {q(drv)}, {arr}, ARRAY_SIZE({arr}) }},\n')
c_parts.append('};\n\n')

c_parts.append(r'''
static const struct tms320_family_desc *tms320_find_family(const char *key)
{
	for (unsigned int i = 0; i < ARRAY_SIZE(tms320_families); i++) {
		if (strcasecmp(key, tms320_families[i].key) == 0 ||
				strcasecmp(key, tms320_families[i].isa) == 0)
			return &tms320_families[i];
	}
	return NULL;
}

static struct tms320_common *target_to_tms320(struct target *target)
{
	return target ? target->arch_info : NULL;
}

static int tms320_unsupported(struct target *target, const char *op)
{
	struct tms320_common *tms320 = target_to_tms320(target);
	LOG_ERROR("TMS320 %s operation is not implemented for family %s. "
		"This backend provides CCS-derived metadata/register IDs; low-level "
		"debug packets require a family-specific TI native transport mapping.",
		op, tms320 && tms320->family ? tms320->family->key : "unset");
	return ERROR_TARGET_RESOURCE_NOT_AVAILABLE;
}

static int tms320_reg_get(struct reg *reg)
{
	/* No public transport is attached here. Return the cached value so GDB and
	 * Tcl can inspect the exact CCS register model without claiming hardware
	 * synchronization. */
	reg->valid = false;
	return ERROR_OK;
}

static int tms320_reg_set(struct reg *reg, uint8_t *buf)
{
	memcpy(reg->value, buf, DIV_ROUND_UP(reg->size, 8));
	reg->dirty = true;
	reg->valid = true;
	return ERROR_OK;
}

static const struct reg_arch_type tms320_reg_type = {
	.get = tms320_reg_get,
	.set = tms320_reg_set,
};

static struct reg_cache *tms320_build_reg_cache(struct target *target)
{
	struct tms320_common *tms320 = target_to_tms320(target);
	const struct tms320_family_desc *family = tms320->family;
	if (!family)
		family = tms320_find_family("c66xx");

	struct reg_cache *cache = calloc(1, sizeof(*cache));
	struct reg *regs = calloc(family->num_regs, sizeof(*regs));
	struct tms320_reg_arch_info *info = calloc(family->num_regs, sizeof(*info));
	uint8_t *values = calloc(family->num_regs, 32);
	if (!cache || !regs || !info || !values) {
		free(cache);
		free(regs);
		free(info);
		free(values);
		return NULL;
	}

	cache->name = family->isa;
	cache->num_regs = family->num_regs;
	cache->reg_list = regs;

	for (unsigned int i = 0; i < family->num_regs; i++) {
		const struct tms320_reg_desc *desc = &family->regs[i];
		info[i].tms320 = tms320;
		info[i].num = i;
		info[i].ti_id = desc->ti_id;
		info[i].address = desc->address;
		info[i].page = desc->page;
		regs[i].name = desc->name;
		regs[i].number = i;
		regs[i].size = desc->bits;
		regs[i].value = values + i * 32;
		regs[i].dirty = false;
		regs[i].valid = false;
		regs[i].exist = true;
		regs[i].caller_save = true;
		regs[i].group = "general";
		regs[i].type = &tms320_reg_type;
		regs[i].arch_info = &info[i];
	}

	tms320->core_cache = cache;
	tms320->reg_values = values;
	tms320->reg_info = info;
	return cache;
}

static int tms320_poll(struct target *target)
{
	if (target->state == TARGET_UNKNOWN)
		target->state = TARGET_RUNNING;
	return ERROR_OK;
}

static int tms320_arch_state(struct target *target)
{
	struct tms320_common *tms320 = target_to_tms320(target);
	LOG_USER("TMS320 target %s: family=%s isa=%s state=%s",
		target_name(target),
		tms320 && tms320->family ? tms320->family->key : "unset",
		tms320 && tms320->family ? tms320->family->isa : "unset",
		target_state_name(target));
	return ERROR_OK;
}

static int tms320_halt(struct target *target)
{
	return tms320_unsupported(target, "halt");
}

static int tms320_resume(struct target *target, bool current,
		target_addr_t address, bool handle_breakpoints, bool debug_execution)
{
	(void)current;
	(void)address;
	(void)handle_breakpoints;
	(void)debug_execution;
	return tms320_unsupported(target, "resume");
}

static int tms320_step(struct target *target, bool current,
		target_addr_t address, bool handle_breakpoints)
{
	(void)current;
	(void)address;
	(void)handle_breakpoints;
	return tms320_unsupported(target, "step");
}

static int tms320_assert_reset(struct target *target)
{
	target->state = TARGET_RESET;
	return ERROR_OK;
}

static int tms320_deassert_reset(struct target *target)
{
	target->state = TARGET_RUNNING;
	return ERROR_OK;
}

static const char *tms320_get_gdb_arch(const struct target *target)
{
	const struct tms320_common *tms320 = target->arch_info;
	return tms320 && tms320->family ? tms320->family->gdb_arch : "tms320";
}

static int tms320_get_gdb_reg_list(struct target *target, struct reg **reg_list[],
		int *reg_list_size, enum target_register_class reg_class)
{
	(void)reg_class;
	struct tms320_common *tms320 = target_to_tms320(target);
	if (!tms320 || !tms320->core_cache)
		return ERROR_FAIL;
	*reg_list_size = tms320->core_cache->num_regs;
	*reg_list = calloc(*reg_list_size, sizeof(struct reg *));
	if (!*reg_list)
		return ERROR_FAIL;
	for (int i = 0; i < *reg_list_size; i++)
		(*reg_list)[i] = &tms320->core_cache->reg_list[i];
	return ERROR_OK;
}

static int tms320_memory_ready(struct target *target)
{
	(void)target;
	return ERROR_TARGET_RESOURCE_NOT_AVAILABLE;
}

static int tms320_read_memory(struct target *target, target_addr_t address,
		uint32_t size, uint32_t count, uint8_t *buffer)
{
	(void)address;
	(void)size;
	(void)count;
	(void)buffer;
	return tms320_unsupported(target, "memory read");
}

static int tms320_write_memory(struct target *target, target_addr_t address,
		uint32_t size, uint32_t count, const uint8_t *buffer)
{
	(void)address;
	(void)size;
	(void)count;
	(void)buffer;
	return tms320_unsupported(target, "memory write");
}

static int tms320_read_buffer(struct target *target, target_addr_t address,
		uint32_t size, uint8_t *buffer)
{
	return tms320_read_memory(target, address, 1, size, buffer);
}

static int tms320_write_buffer(struct target *target, target_addr_t address,
		uint32_t size, const uint8_t *buffer)
{
	return tms320_write_memory(target, address, 1, size, buffer);
}

static int tms320_address_bits(struct target *target)
{
	struct tms320_common *tms320 = target_to_tms320(target);
	if (tms320 && tms320->family &&
			(strstr(tms320->family->key, "c71") || strstr(tms320->family->key, "c75")))
		return 64;
	return 32;
}

static int tms320_data_bits(struct target *target)
{
	(void)target;
	return 32;
}

static int tms320_init_target(struct command_context *cmd_ctx, struct target *target)
{
	(void)cmd_ctx;
	struct tms320_common *tms320 = target_to_tms320(target);
	if (!tms320)
		return ERROR_FAIL;
	if (!tms320->family)
		tms320->family = tms320_find_family("c66xx");
	if (!tms320->procid && tms320->family)
		tms320->procid = tms320->family->procid;
	target->endianness = TARGET_LITTLE_ENDIAN;
	target->state = TARGET_UNKNOWN;
	target->debug_reason = DBG_REASON_UNDEFINED;
	target->reg_cache = tms320_build_reg_cache(target);
	return target->reg_cache ? ERROR_OK : ERROR_FAIL;
}

static int tms320_target_create(struct target *target)
{
	struct tms320_common *tms320 = calloc(1, sizeof(*tms320));
	if (!tms320)
		return ERROR_FAIL;
	tms320->target = target;
	tms320->family = tms320_find_family("c66xx");
	if (tms320->family)
		tms320->procid = tms320->family->procid;
	target->arch_info = tms320;
	return ERROR_OK;
}

static void tms320_deinit_target(struct target *target)
{
	struct tms320_common *tms320 = target_to_tms320(target);
	if (!tms320)
		return;
	if (tms320->core_cache) {
		free(tms320->core_cache->reg_list);
		free(tms320->core_cache);
	}
	free(tms320->reg_values);
	free(tms320->reg_info);
	free(tms320->device_name);
	free(tms320->core_name);
	free(tms320->gel_file);
	free(tms320);
}

static int tms320_examine(struct target *target)
{
	target_set_examined(target);
	return ERROR_OK;
}

static int tms320_set_string(char **slot, const char *value)
{
	char *copy = strdup(value ? value : "");
	if (!copy)
		return ERROR_FAIL;
	free(*slot);
	*slot = copy;
	return ERROR_OK;
}

COMMAND_HANDLER(tms320_handle_family_command)
{
	struct target *target = get_current_target(CMD_CTX);
	struct tms320_common *tms320 = target_to_tms320(target);
	if (!tms320)
		return ERROR_FAIL;
	if (CMD_ARGC == 0) {
		command_print(CMD, "%s", tms320->family ? tms320->family->key : "unset");
		return ERROR_OK;
	}
	if (CMD_ARGC != 1)
		return ERROR_COMMAND_SYNTAX_ERROR;
	const struct tms320_family_desc *family = tms320_find_family(CMD_ARGV[0]);
	if (!family) {
		command_print(CMD, "unknown TMS320 family '%s'", CMD_ARGV[0]);
		command_print(CMD, "known families:");
		for (unsigned int i = 0; i < ARRAY_SIZE(tms320_families); i++)
			command_print(CMD, "  %s (%s)", tms320_families[i].key, tms320_families[i].isa);
		return ERROR_COMMAND_ARGUMENT_INVALID;
	}
	tms320->family = family;
	tms320->procid = family->procid;
	return ERROR_OK;
}

COMMAND_HANDLER(tms320_handle_string_command)
{
	struct target *target = get_current_target(CMD_CTX);
	struct tms320_common *tms320 = target_to_tms320(target);
	char **slot = NULL;
	if (!tms320)
		return ERROR_FAIL;
	if (strcmp(CMD_NAME, "device") == 0)
		slot = &tms320->device_name;
	else if (strcmp(CMD_NAME, "core") == 0)
		slot = &tms320->core_name;
	else if (strcmp(CMD_NAME, "gel_file") == 0)
		slot = &tms320->gel_file;
	else
		return ERROR_FAIL;
	if (CMD_ARGC == 0) {
		command_print(CMD, "%s", *slot ? *slot : "unset");
		return ERROR_OK;
	}
	if (CMD_ARGC != 1)
		return ERROR_COMMAND_SYNTAX_ERROR;
	return tms320_set_string(slot, CMD_ARGV[0]);
}

COMMAND_HANDLER(tms320_handle_procid_command)
{
	struct target *target = get_current_target(CMD_CTX);
	struct tms320_common *tms320 = target_to_tms320(target);
	if (!tms320)
		return ERROR_FAIL;
	if (CMD_ARGC == 0) {
		command_print(CMD, "0x%08" PRIx32, tms320->procid);
		return ERROR_OK;
	}
	if (CMD_ARGC != 1)
		return ERROR_COMMAND_SYNTAX_ERROR;
	COMMAND_PARSE_NUMBER(u32, CMD_ARGV[0], tms320->procid);
	return ERROR_OK;
}

COMMAND_HANDLER(tms320_handle_icepick_port_command)
{
	struct target *target = get_current_target(CMD_CTX);
	struct tms320_common *tms320 = target_to_tms320(target);
	if (!tms320)
		return ERROR_FAIL;
	if (CMD_ARGC == 0) {
		if (tms320->icepick_port_valid)
			command_print(CMD, "0x%02" PRIx32, tms320->icepick_port);
		else
			command_print(CMD, "unset");
		return ERROR_OK;
	}
	if (CMD_ARGC != 1)
		return ERROR_COMMAND_SYNTAX_ERROR;
	COMMAND_PARSE_NUMBER(u32, CMD_ARGV[0], tms320->icepick_port);
	tms320->icepick_port_valid = true;
	return ERROR_OK;
}

COMMAND_HANDLER(tms320_handle_info_command)
{
	struct target *target = get_current_target(CMD_CTX);
	struct tms320_common *tms320 = target_to_tms320(target);
	if (!tms320 || !tms320->family)
		return ERROR_FAIL;
	command_print(CMD, "TMS320 target '%s'", target_name(target));
	command_print(CMD, "  device: %s", tms320->device_name ? tms320->device_name : "unset");
	command_print(CMD, "  core: %s", tms320->core_name ? tms320->core_name : "unset");
	command_print(CMD, "  family: %s", tms320->family->key);
	command_print(CMD, "  ISA: %s", tms320->family->isa);
	command_print(CMD, "  GDB arch: %s", tms320->family->gdb_arch);
	command_print(CMD, "  CCS ProcID: 0x%08" PRIx32, tms320->procid);
	command_print(CMD, "  CCS driver: %s", tms320->family->driver);
	if (tms320->icepick_port_valid)
		command_print(CMD, "  ICEPick port: 0x%02" PRIx32, tms320->icepick_port);
	else
		command_print(CMD, "  ICEPick port: direct-or-unset");
	command_print(CMD, "  GEL file: %s", tms320->gel_file ? tms320->gel_file : "unset");
	command_print(CMD, "  register IDs: %u", tms320->family->num_regs);
	return ERROR_OK;
}

COMMAND_HANDLER(tms320_handle_regids_command)
{
	struct target *target = get_current_target(CMD_CTX);
	struct tms320_common *tms320 = target_to_tms320(target);
	if (!tms320 || !tms320->family)
		return ERROR_FAIL;
	for (unsigned int i = 0; i < tms320->family->num_regs; i++) {
		const struct tms320_reg_desc *r = &tms320->family->regs[i];
		command_print(CMD, "%3u %-24s id=%d addr=0x%08" PRIx32 " page=%u bits=%u",
			i, r->name, r->ti_id, r->address, r->page, r->bits);
	}
	return ERROR_OK;
}

static const struct command_registration tms320_exec_command_handlers[] = {
	{ .name = "info", .handler = tms320_handle_info_command, .mode = COMMAND_EXEC,
		.help = "show CCS-derived TMS320 target metadata" },
	{ .name = "family", .handler = tms320_handle_family_command, .mode = COMMAND_ANY,
		.help = "get or set TMS320 CPU family", .usage = "[c55xx|c64xx|c64xp|c646x|c66xx|c674x|c620x|c621x|c670x|c671x|c672x|c71x|c75x]" },
	{ .name = "device", .handler = tms320_handle_string_command, .mode = COMMAND_ANY,
		.help = "get or set CCS targetdb device name", .usage = "[name]" },
	{ .name = "core", .handler = tms320_handle_string_command, .mode = COMMAND_ANY,
		.help = "get or set CCS targetdb core name", .usage = "[name]" },
	{ .name = "gel_file", .handler = tms320_handle_string_command, .mode = COMMAND_ANY,
		.help = "get or set CCS GEL file", .usage = "[path]" },
	{ .name = "procid", .handler = tms320_handle_procid_command, .mode = COMMAND_ANY,
		.help = "get or set CCS driver ProcID", .usage = "[value]" },
	{ .name = "icepick_port", .handler = tms320_handle_icepick_port_command, .mode = COMMAND_ANY,
		.help = "get or set ICEPick port number", .usage = "[port]" },
	{ .name = "regids", .handler = tms320_handle_regids_command, .mode = COMMAND_EXEC,
		.help = "show CCS-derived register IDs for the current TMS320 family" },
	COMMAND_REGISTRATION_DONE
};

static const struct command_registration tms320_command_handlers[] = {
	{ .name = "tms320", .mode = COMMAND_ANY, .help = "TI TMS320 DSP target commands",
		.chain = tms320_exec_command_handlers },
	COMMAND_REGISTRATION_DONE
};

struct target_type tms320_target = {
	.name = "tms320",
	.poll = tms320_poll,
	.arch_state = tms320_arch_state,
	.halt = tms320_halt,
	.resume = tms320_resume,
	.step = tms320_step,
	.assert_reset = tms320_assert_reset,
	.deassert_reset = tms320_deassert_reset,
	.get_gdb_arch = tms320_get_gdb_arch,
	.get_gdb_reg_list = tms320_get_gdb_reg_list,
	.get_gdb_reg_list_noread = tms320_get_gdb_reg_list,
	.memory_ready = tms320_memory_ready,
	.read_memory = tms320_read_memory,
	.write_memory = tms320_write_memory,
	.read_buffer = tms320_read_buffer,
	.write_buffer = tms320_write_buffer,
	.commands = tms320_command_handlers,
	.target_create = tms320_target_create,
	.init_target = tms320_init_target,
	.deinit_target = tms320_deinit_target,
	.examine = tms320_examine,
	.address_bits = tms320_address_bits,
	.data_bits = tms320_data_bits,
};
''')
(repo/'src/target/tms320.c').write_text(''.join(c_parts))

# patch Makefile and target registration
for file, repls in {
    repo/'src/target/Makefile.am': [('%D%/c28x.c \\\n', '%D%/c28x.c \\\n\t%D%/tms320.c \\\n'), ('%D%/c28x.h \\\n', '%D%/c28x.h \\\n\t%D%/tms320.h \\\n')],
    repo/'src/target/target_type.h': [('extern struct target_type testee_target;\n', 'extern struct target_type testee_target;\nextern struct target_type tms320_target;\n')],
    repo/'src/target/target.c': [('\t&testee_target,\n', '\t&testee_target,\n\t&tms320_target,\n')],
}.items():
    s=file.read_text()
    for a,b in repls:
        if b not in s:
            s=s.replace(a,b)
    file.write_text(s)

# Generate target configs
outdir = repo/'tcl/target/ti/tms320/generated'
outdir.mkdir(parents=True, exist_ok=True)

recognized = set(['TMS320C28XX','TMS320C28xx']) | set(isa_to_family.keys())
procid_by_family = {fam: family_specs[fam][3] for fam in family_specs}


def slug(part):
    s=part.lower()
    s=s.replace('-','_')
    s=re.sub(r'[^a-z0-9_]+','_',s)
    return s.strip('_')

def get_gel(cpu):
    for p in cpu.findall('.//property'):
        if p.attrib.get('id') == 'GEL File':
            return p.attrib.get('Value','')
    return ''

def walk(node, part, port=None, out=None):
    if out is None: out=[]
    local_port = port
    for child in list(node):
        if child.tag == 'property' and child.attrib.get('id') == 'Port Number':
            local_port = child.attrib.get('Value')
            continue
        if child.tag == 'cpu':
            isa = child.attrib.get('isa','')
            if isa in recognized:
                out.append({
                    'id': child.attrib.get('id','cpu'),
                    'isa': isa,
                    'port': local_port,
                    'gel': get_gel(child),
                })
            walk(child, part, local_port, out)
        else:
            walk(child, part, local_port, out)
    return out

index=[]
dev_summaries=[]
for n in sorted(z.namelist()):
    if not n.startswith('ccs_base/common/targetdb/devices/') or not n.endswith('.xml'):
        continue
    try:
        root = ET.fromstring(z.read(n).decode('utf-8', errors='ignore'))
    except Exception:
        continue
    part = root.attrib.get('partnum') or root.attrib.get('desc') or Path(n).stem
    cpus = walk(root, part)
    if not cpus:
        continue
    # Include only named TMS320 parts plus devices containing non-C28x TMS320 DSPs.
    if not re.match(r'(?i)^(tms320|f28m|f28p|f28e|f29|c[0-9]|r28)', part) and all(c['isa'].lower().startswith('tms320c28') for c in cpus):
        continue
    fn = slug(part) + '.cfg'
    index.append((fn, part, cpus))
    lines=[]
    lines.append('# SPDX-License-Identifier: GPL-2.0-or-later\n')
    lines.append(f'# Generated from CCS targetdb device XML: {n}\n')
    lines.append(f'# Device: {part}\n\n')
    lines.append('if { ![info exists CHIPNAME] } {\n')
    lines.append(f'\tset CHIPNAME {slug(part)}\n')
    lines.append('}\n\n')
    if any(c['isa'].lower().startswith('tms320c28') for c in cpus):
        lines.append('source [find target/ti/c2000-icepick-scan.cfg]\n\n')
    else:
        lines.append('source [find target/ti/tms320-generic-scan.cfg]\n\n')
    count=0
    for c in cpus:
        isa=c['isa']; cid=sanitize_c(c['id']).lower(); count+=1
        tname=f'${{CHIPNAME}}.{cid}'
        if isa.lower().startswith('tms320c28'):
            lines.append(f'# {c["id"]}: {isa}\n')
            lines.append(f'set _TARGETNAME_{count} {tname}\n')
            lines.append(f'target create $_TARGETNAME_{count} c28x -chain-position $C2000_ICEPICK_TAP_NAME\n')
            lines.append(f'targets $_TARGETNAME_{count}\n')
            lines.append(f'c28x device {part}\n')
            lines.append('c28x procid 0x5000A3F8\n')
            if c['port']:
                lines.append(f'c28x icepick_port {c["port"]}\n')
            if c['gel']:
                lines.append(f'c28x gel_file {c["gel"].replace("\\", "/")}\n')
            lines.append('\n')
        else:
            fam=isa_to_family[isa]
            lines.append(f'# {c["id"]}: {isa}\n')
            lines.append(f'set _TARGETNAME_{count} {tname}\n')
            lines.append(f'target create $_TARGETNAME_{count} tms320 -chain-position $TMS320_GENERIC_TAP_NAME\n')
            lines.append(f'targets $_TARGETNAME_{count}\n')
            lines.append(f'tms320 family {fam}\n')
            lines.append(f'tms320 device {part}\n')
            lines.append(f'tms320 core {c["id"]}\n')
            lines.append(f'tms320 procid {procid_by_family[fam]}\n')
            if c['port']:
                lines.append(f'tms320 icepick_port {c["port"]}\n')
            if c['gel']:
                lines.append(f'tms320 gel_file {c["gel"].replace("\\", "/")}\n')
            lines.append('\n')
    lines.append('targets $_TARGETNAME_1\n')
    (outdir/fn).write_text(''.join(lines))
    fams=sorted(set('c28x' if c['isa'].lower().startswith('tms320c28') else isa_to_family[c['isa']] for c in cpus))
    dev_summaries.append((part, fn, ','.join(fams), len(cpus)))

# common scan file
(repo/'tcl/target/ti/tms320-generic-scan.cfg').write_text('''# SPDX-License-Identifier: GPL-2.0-or-later\n#\n# Generic TI TMS320 JTAG TAP declaration for CCS-derived metadata targets.\n# Device-specific files may override TMS320_IRLEN/TMS320_TAPID before sourcing.\n\nif { ![info exists CHIPNAME] } {\n\terror "CHIPNAME must be set before target/ti/tms320-generic-scan.cfg"\n}\n\nif { ![info exists TMS320_IRLEN] } {\n\tset TMS320_IRLEN 6\n}\n\nset _TMS320_CHIPNAME $CHIPNAME\nset _TMS320_TAP $_TMS320_CHIPNAME.tms320\nset _tms320_newtap [list jtag newtap $_TMS320_CHIPNAME tms320 \\\n\t-irlen $TMS320_IRLEN -ircapture 0x1 -irmask 0x3]\n\nif { [info exists TMS320_TAPID] } {\n\tlappend _tms320_newtap -expected-id $TMS320_TAPID\n}\n\neval $_tms320_newtap\nset TMS320_GENERIC_TAP_NAME $_TMS320_TAP\n''')

# Index and docs
idx_lines=['# SPDX-License-Identifier: GPL-2.0-or-later\n', '# Generated CCS-derived TMS320 target configuration index.\n', '# Source one of the generated/*.cfg files directly.\n\n']
for fn,part,cpus in index:
    fams=','.join(sorted(set('c28x' if c['isa'].lower().startswith('tms320c28') else isa_to_family[c['isa']] for c in cpus)))
    idx_lines.append(f'# {part}: {fams} -> target/ti/tms320/generated/{fn}\n')
(repo/'tcl/target/ti/tms320/index.cfg').write_text(''.join(idx_lines))

md=[]
md.append('# TI TMS320 family support generated from CCS targetdb\n\n')
md.append('This repository imports TI Code Composer Studio `ccs_base` target metadata to broaden OpenOCD coverage across TMS320 DSP families.\n\n')
md.append('## Implemented layers\n\n')
md.append('- `c28x` remains the real C28x/C2000 OpenOCD target backend with CCS-derived register IDs and recovered GTI/TRG operation metadata.\n')
md.append('- `tms320` is a generic metadata/debug-model backend for non-C28x TMS320 DSP families: C55x, C62x/C64x/C64x+/C646x/C66x/C674x, C71x and C75x.\n')
md.append('- Generated target configs live under `tcl/target/ti/tms320/generated/`.\n')
md.append('- Register-ID tables are generated from `common/targetdb/drivers/TI_reg_ids/*.xml`.\n')
md.append('- Device/core/GEL/ICEPick metadata is generated from `common/targetdb/devices/*.xml`.\n\n')
md.append('## Safety boundary\n\n')
md.append('The non-C28x `tms320` backend intentionally fails closed for halt/resume/step/memory operations. CCS exposes these through TI-private native drivers (`tixds55x.dvr`, `tixds6400_plus.dvr`, `tixds510c71x.dvr`, etc.); the public XML gives exact register IDs and ProcIDs but not a complete public JTAG packet protocol.\n\n')
md.append('## Family register coverage\n\n')
md.append('| Family | ISA | ProcID | CCS driver | Register IDs |\n')
md.append('|---|---:|---:|---|---:|\n')
for fam,(regfile,cpufile,isa,procid,drv) in family_specs.items():
    md.append(f'| `{fam}` | `{isa}` | `{procid}` | `{drv}` | {len(family_regs[fam])} |\n')
md.append('\n## Generated device configs\n\n')
md.append(f'Generated {len(index)} device configuration files.\n\n')
for part,fn,fams,ncpu in sorted(dev_summaries)[:500]:
    md.append(f'- `{part}`: `{fams}`, {ncpu} CPU target(s), `target/ti/tms320/generated/{fn}`\n')
(repo/'docs/targets/ti-tms320-family-support.md').write_text(''.join(md))

# generation script copied into repo
script_dir=repo/'contrib/ti-tms320'
script_dir.mkdir(exist_ok=True)
Path('/mnt/data/generate_tms320_support.py').replace(script_dir/'generate_tms320_support.py')

print('generated families', len(family_specs), 'configs', len(index))
