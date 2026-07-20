/* SPDX-License-Identifier: GPL-2.0-or-later */

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
