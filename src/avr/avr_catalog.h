/* SPDX-License-Identifier: GPL-2.0-or-later */

#ifndef OPENOCD_AVR_CATALOG_H
#define OPENOCD_AVR_CATALOG_H

#include <stddef.h>

struct command_context;

struct avr_catalog_mcu {
	const char *id;
	const char *aliases;
	const char *description;
	const char *parent;
	const char *signature;
	const char *interfaces;
	const char *memories;
};

struct avr_catalog_programmer {
	const char *id;
	const char *aliases;
	const char *description;
	const char *parent;
	const char *type;
	const char *prog_modes;
	const char *connection_type;
	const char *usbvid;
	const char *usbpid;
	const char *usbvendor;
	const char *usbproduct;
};

extern const struct avr_catalog_mcu avr_catalog_mcus[];
extern const size_t avr_catalog_mcu_count;
extern const struct avr_catalog_programmer avr_catalog_programmers[];
extern const size_t avr_catalog_programmer_count;
extern const char avr_catalog_source[];
extern const char avr_catalog_source_sha256[];

int avr_catalog_register_commands(struct command_context *cmd_ctx);

#endif /* OPENOCD_AVR_CATALOG_H */
