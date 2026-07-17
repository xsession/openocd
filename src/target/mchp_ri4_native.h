/* SPDX-License-Identifier: GPL-2.0-or-later */

#ifndef OPENOCD_TARGET_MCHP_RI4_NATIVE_H
#define OPENOCD_TARGET_MCHP_RI4_NATIVE_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

struct mchp_ri4_native;

struct mchp_ri4_native_config {
	uint16_t vid;
	uint16_t pid;
	const char *serial;
	const char *processor;
	const char *family;
	const char *scripts_path;
	const char *tool_scripts_path;
	const char *script_suffix;
};

struct mchp_ri4_native_caps {
	bool erase;
	bool debug;
	bool poll;
	bool set_pc;
	bool breakpoints;
	bool watchpoints;
	bool memory_read;
	bool memory_write;
};

int mchp_ri4_native_open(struct mchp_ri4_native **session,
	const struct mchp_ri4_native_config *config);
void mchp_ri4_native_close(struct mchp_ri4_native *session);
void mchp_ri4_native_get_caps(struct mchp_ri4_native *session,
	struct mchp_ri4_native_caps *caps);

int mchp_ri4_native_enter_debug(struct mchp_ri4_native *session);
int mchp_ri4_native_halt(struct mchp_ri4_native *session);
int mchp_ri4_native_run(struct mchp_ri4_native *session);
int mchp_ri4_native_step(struct mchp_ri4_native *session);
int mchp_ri4_native_reset(struct mchp_ri4_native *session);
int mchp_ri4_native_is_halted(struct mchp_ri4_native *session, bool *halted);
int mchp_ri4_native_get_pc(struct mchp_ri4_native *session,
	unsigned int pc_bytes, uint32_t *pc);
int mchp_ri4_native_set_pc(struct mchp_ri4_native *session, uint32_t pc);
int mchp_ri4_native_read(struct mchp_ri4_native *session,
	uint32_t address, uint8_t *data, uint32_t length);
int mchp_ri4_native_write(struct mchp_ri4_native *session,
	uint32_t address, const uint8_t *data, uint32_t length);
int mchp_ri4_native_erase(struct mchp_ri4_native *session, unsigned int mode);
int mchp_ri4_native_set_breakpoint(struct mchp_ri4_native *session,
	unsigned int slot, uint32_t address);
int mchp_ri4_native_set_watchpoint(struct mchp_ri4_native *session,
	unsigned int access, unsigned int slot, uint32_t address);
int mchp_ri4_native_clear_point(struct mchp_ri4_native *session,
	unsigned int slot);

#endif /* OPENOCD_TARGET_MCHP_RI4_NATIVE_H */
