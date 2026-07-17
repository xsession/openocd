// SPDX-License-Identifier: GPL-2.0-or-later
#ifndef OPENOCD_TARGET_MCHP_RI4_BRIDGE_H
#define OPENOCD_TARGET_MCHP_RI4_BRIDGE_H

#include <stdbool.h>

struct target;

bool mchp_ri4_bridge_is_target(const struct target *target);
int mchp_ri4_bridge_mass_erase(struct target *target, unsigned int mode);

#endif /* OPENOCD_TARGET_MCHP_RI4_BRIDGE_H */
