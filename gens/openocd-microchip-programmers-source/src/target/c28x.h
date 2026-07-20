/* SPDX-License-Identifier: GPL-2.0-or-later */

#ifndef OPENOCD_TARGET_C28X_H
#define OPENOCD_TARGET_C28X_H

#include "target.h"
#include "register.h"

#define C28X_MAX_HW_BREAKPOINTS 8
#define C28X_MAX_HW_WATCHPOINTS 8

struct c28x_common;

struct c28x_core_reg {
	struct c28x_common *c28x;
	unsigned int num;
	uint32_t ti_id;
	const char *name;
};

struct c28x_scan_ir {
	bool valid;
	uint32_t value;
};

struct c28x_common {
	struct target *target;
	struct reg_cache *core_cache;
	uint8_t *reg_values;
	struct c28x_core_reg *reg_info;

	char *gdb_arch;
	char *device_name;
	char *gel_file;
	uint32_t ti_proc_id;
	uint32_t icepick_port;
	bool icepick_port_valid;
	uint32_t xds110_memread_cmd;
	uint32_t xds110_memwrite_cmd;
	uint32_t status_value;
	uint32_t status_halt_mask;
	uint32_t status_run_mask;
	unsigned int status_dr_bits;
	unsigned int raw_data_dr_bits;
	bool transport_enabled;

	struct c28x_scan_ir ir_idcode;
	struct c28x_scan_ir ir_status;
	struct c28x_scan_ir ir_halt;
	struct c28x_scan_ir ir_resume;
	struct c28x_scan_ir ir_step;
	struct c28x_scan_ir ir_reg_read;
	struct c28x_scan_ir ir_reg_write;
	struct c28x_scan_ir ir_mem_read16;
	struct c28x_scan_ir ir_mem_write16;
	struct c28x_scan_ir ir_bp_write;
	struct c28x_scan_ir ir_wp_write;
	struct c28x_scan_ir ir_bypass;

	bool hw_breakpoint_used[C28X_MAX_HW_BREAKPOINTS];
	bool hw_watchpoint_used[C28X_MAX_HW_WATCHPOINTS];
};

struct c28x_common *target_to_c28x(struct target *target);

#endif /* OPENOCD_TARGET_C28X_H */
