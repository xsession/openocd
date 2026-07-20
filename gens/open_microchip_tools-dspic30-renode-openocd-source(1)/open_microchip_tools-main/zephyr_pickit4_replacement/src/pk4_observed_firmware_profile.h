#ifndef ZEPHYR_PICKIT4_REPLACEMENT_PK4_OBSERVED_FIRMWARE_PROFILE_H_
#define ZEPHYR_PICKIT4_REPLACEMENT_PK4_OBSERVED_FIRMWARE_PROFILE_H_

#include <stdint.h>

/*
 * Clean-room summary of the vendored PK4 boot/app blobs.
 * These constants are derived from observed Intel HEX layout and vector tables,
 * not from copied vendor source.
 */

#define PK4_OBS_BOOT_BASE           0x00400000U
#define PK4_OBS_APP_BASE            0x0040C000U
#define PK4_OBS_APP2_BASE           0x00500000U

#define PK4_OBS_BOOT_INITIAL_SP     0x2040DC08U
#define PK4_OBS_BOOT_RESET_VECTOR   0x004001ADU

#define PK4_OBS_APP_INITIAL_SP      0x20449460U
#define PK4_OBS_APP_RESET_VECTOR    0x0040E8ADU

#define PK4_OBS_APP2_INITIAL_SP     0x2040A910U
#define PK4_OBS_APP2_RESET_VECTOR   0x00504189U

#define PK4_OBS_RAM_REGION_BASE     0x20400000U
#define PK4_OBS_ARCH_CORTEX_M       1U
#define PK4_OBS_APP2_IDENTITY       "MPLAB PICkit 4 CMSIS-DAP"

#endif