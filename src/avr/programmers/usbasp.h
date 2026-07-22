/* SPDX-License-Identifier: GPL-2.0-or-later */

#ifndef OPENOCD_AVR_PROGRAMMERS_USBASP_H
#define OPENOCD_AVR_PROGRAMMERS_USBASP_H

struct command_context;

extern const char avr_usbasp_backend_status[];

int avr_usbasp_register_commands(struct command_context *cmd_ctx);

#endif /* OPENOCD_AVR_PROGRAMMERS_USBASP_H */
