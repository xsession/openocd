/* SPDX-License-Identifier: GPL-2.0-or-later */

#ifndef OPENOCD_AVRDUDE_CATALOG_H
#define OPENOCD_AVRDUDE_CATALOG_H

#include <stddef.h>

struct command_context;

struct avrdude_catalog_part {
	const char *id;
	const char *aliases;
	const char *description;
	const char *parent;
	const char *signature;
	const char *interfaces;
	const char *memories;
};

struct avrdude_catalog_programmer {
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

extern const struct avrdude_catalog_part avrdude_catalog_parts[];
extern const size_t avrdude_catalog_part_count;
extern const struct avrdude_catalog_programmer avrdude_catalog_programmers[];
extern const size_t avrdude_catalog_programmer_count;
extern const char avrdude_catalog_source[];
extern const char avrdude_catalog_source_sha256[];

int avrdude_catalog_register_commands(struct command_context *cmd_ctx);

#endif /* OPENOCD_AVRDUDE_CATALOG_H */
