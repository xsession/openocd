/* SPDX-License-Identifier: GPL-2.0-or-later */

/*
 * Copyright (C) 2026 Texas Instruments Incorporated - https://www.ti.com/
 *
 * Flash loader algorithm parameters for AM13E230X.
 * Addresses must match the linker script in
 * contrib/loaders/flash/am13e230x/am13e230x.lds
 */

#ifndef OPENOCD_FLASH_NOR_AM13E230X_H
#define OPENOCD_FLASH_NOR_AM13E230X_H

/* Algorithm is loaded at the base of SRAM */
#define AM13_ALGO_BASE 0x20000000

/* Parameter blocks (two, for ping-pong) */
#define AM13_ALGO_PARAMS_0 0x20002000
#define AM13_ALGO_PARAMS_1 0x20002014

/* Data buffers (each one sector = 2 KB) */
#define AM13_ALGO_BUFFER_0 0x20002100
#define AM13_ALGO_BUFFER_1 0x20002900

/* Total working area needed */
#define AM13_ALGO_WORKING_SIZE (AM13_ALGO_BUFFER_1 + 0x800 - AM13_ALGO_BASE)

/* Handshake values (must match loader main.c) */
#define AM13_BUFFER_EMPTY 0x00000000
#define AM13_BUFFER_FULL 0xFFFFFFFF

/* Offset of the status field within flash_params */
#define AM13_STATUS_OFFSET 0x0C

/* Commands (must match loader main.c) */
#define AM13_CMD_NO_ACTION 0
#define AM13_CMD_ERASE_ALL 1
#define AM13_CMD_PROGRAM 2
#define AM13_CMD_ERASE_AND_PROGRAM 3
#define AM13_CMD_ERASE_SECTORS 4

/* Parameter block layout (matches struct flash_params in loader) */
struct am13_algo_params
{
	uint8_t dest[4];
	uint8_t len[4];
	uint8_t cmd[4];
	uint8_t status[4];
	uint8_t buf_addr[4];
};

#endif /* OPENOCD_FLASH_NOR_AM13E230X_H */
