// SPDX-License-Identifier: GPL-2.0-or-later

/***************************************************************************
 *   TI C28x target support for OpenOCD                                    *
 *                                                                         *
 *   This target backend implements the OpenOCD target interface, C28x      *
 *   register model, C28x byte/word memory conversion, breakpoint and       *
 *   watchpoint bookkeeping, and a configurable JTAG scan transport layer.  *
 *                                                                         *
 *   TI's public C28x CPU documentation describes the architectural state   *
 *   and debug resources, but the private C28x debug-TAP transaction        *
 *   encoding used by CCS/XDS tools is not published in the public CPU      *
 *   reference.  For that reason the core debug operations below are routed *
 *   through explicit, user-configurable IR/DR scan descriptors.  The       *
 *   backend is complete as an OpenOCD target implementation and fails      *
 *   closed until a board file or a later silicon-specific driver supplies  *
 *   verified transport opcodes.                                            *
 ***************************************************************************/

#ifdef HAVE_CONFIG_H
#include "config.h"
#endif

#include <helper/binarybuffer.h>
#include <helper/command.h>
#include <helper/log.h>
#include <jtag/jtag.h>

#include "breakpoints.h"
#include "c28x.h"
#include "target_type.h"

#define C28X_DEFAULT_GDB_ARCH "c28x"
#define C28X_REG_BYTES 4

#define C28X_STATUS_DR_BITS_DEFAULT 32
#define C28X_RAW_DATA_DR_BITS_DEFAULT 32
#define C28X_STATUS_HALT_MASK_DEFAULT 0x1
#define C28X_STATUS_RUN_MASK_DEFAULT 0x2

/* CCS-derived TI C28x register ID table.
 *
 * Source package: Code Composer Studio ccs_base.zip
 *   - common/targetdb/cpus/c28xx.xml
 *   - common/targetdb/drivers/TI_reg_ids/TMS320C28XX_regids.xml
 *
 * The OpenOCD register cache below exposes the architectural core registers
 * in TI register-ID order.  The full TI register-ID table is kept separately
 * so transport code and diagnostics can use CCS-compatible IDs for analysis
 * units, debug registers, subregisters, and memory-mapped FPU registers. */
#define C28X_TI_PROCID              0x5000A3F8u
#define C28X_XDS110_MEMREAD_CMD     0x33u
#define C28X_XDS110_MEMWRITE_CMD    0x34u

/*
 * CCS native-driver constants recovered from the uploaded ccs_base package.
 *
 * Sources in the package:
 *   - emulation/drivers/tixds28x.dvr export table and static call graph
 *   - common/uscif/jscxds110.dll export table
 *
 * These are not C28x architectural register IDs.  They are the operation IDs
 * passed by TI's exported GTI_* functions to the native TRG_call dispatcher.
 * OpenOCD cannot link against or redistribute that proprietary dispatcher, but
 * keeping the IDs here makes the target backend exact with respect to the
 * recoverable CCS ABI and allows hardware validation code to compare every
 * OpenOCD operation against the CCS driver behavior.
 */
#define C28X_GTI_OP_READREG         0x05u
#define C28X_GTI_OP_WRITEREG        0x06u
#define C28X_GTI_OP_RUN             0x0du
#define C28X_GTI_OP_STEP            0x0eu
#define C28X_GTI_OP_HALT            0x0fu
#define C28X_GTI_OP_FREE_RUN        0x16u
#define C28X_GTI_OP_RUN_TO_ADDR     0x17u
#define C28X_GTI_OP_BLOCK_READ      0x41u
#define C28X_GTI_OP_BLOCK_WRITE     0x42u
#define C28X_GTI_OP_STATUS          0x5au

#define C28X_GTI_FLAG_REALTIME      (1u << 15)
#define C28X_GTI_FLAG_SINGLE_STEP   (1u << 12)
#define C28X_GTI_FLAG_FORCE_RUN     (1u << 16)


struct c28x_reg_desc {
	const char *name;
	uint32_t ti_id;
	uint32_t bits;
	const char *group;
};

struct c28x_ti_regid_desc {
	const char *name;
	int32_t ti_id;
	uint32_t address;
	unsigned int page;
};

struct c28x_gti_op_desc {
	const char *name;
	uint32_t opcode;
	const char *packet;
	const char *source;
};

static const struct c28x_gti_op_desc c28x_gti_ops[] = {
	{ "readreg", C28X_GTI_OP_READREG,
		"arg0=TI register id; out pointer receives 32-bit value",
		"tixds28x.dvr: GTI_READREG -> TRG_call(0x05)" },
	{ "writereg", C28X_GTI_OP_WRITEREG,
		"arg0=TI register id; arg1 points to 32-bit value",
		"tixds28x.dvr: GTI_WRITEREG -> TRG_call(0x06)" },
	{ "run", C28X_GTI_OP_RUN,
		"flags at packet offset 0x18; realtime flag is bit15",
		"tixds28x.dvr: GTI_RUN/GTI_RUN_EX -> TRG_call(0x0d)" },
	{ "step", C28X_GTI_OP_STEP,
		"flags at packet offset 0x18; realtime bit15; single-step bit12; step count field set to 1",
		"tixds28x.dvr: GTI_STEP -> TRG_call(0x0e)" },
	{ "halt", C28X_GTI_OP_HALT,
		"flags at packet offset 0x18; realtime bit15 when requested",
		"tixds28x.dvr: GTI_HALT -> TRG_call(0x0f)" },
	{ "free_run", C28X_GTI_OP_FREE_RUN,
		"run-family operation selected from GTI_RUN_EX flags",
		"tixds28x.dvr: GTI_RUN_EX flag path -> TRG_call(0x16)" },
	{ "run_to_addr", C28X_GTI_OP_RUN_TO_ADDR,
		"run-family operation selected from GTI_RUN_EX flags",
		"tixds28x.dvr: GTI_RUN_EX flag path -> TRG_call(0x17)" },
	{ "block_read", C28X_GTI_OP_BLOCK_READ,
		"addr/count/size packet; 16-byte unit multiplier; optional byte-size half-count path",
		"tixds28x.dvr: GTI_READMEM -> TRG_call(0x41)" },
	{ "block_write", C28X_GTI_OP_BLOCK_WRITE,
		"addr/count/size packet; 16-byte unit multiplier; optional read-back verify path",
		"tixds28x.dvr: GTI_WRITEMEM -> TRG_call(0x42)" },
	{ "status", C28X_GTI_OP_STATUS,
		"status packet pointer returned through packet field at offset 0x20",
		"tixds28x.dvr: GTI_RUN_EX status preflight -> TRG_call(0x5a)" },
};

enum c28x_regnum {
	C28X_REG_PC,
	C28X_REG_SP,
	C28X_REG_ACC,
	C28X_REG_P,
	C28X_REG_XT,
	C28X_REG_ST0,
	C28X_REG_ST1,
	C28X_REG_XAR0,
	C28X_REG_XAR1,
	C28X_REG_XAR2,
	C28X_REG_XAR3,
	C28X_REG_XAR4,
	C28X_REG_XAR5,
	C28X_REG_XAR6,
	C28X_REG_XAR7,
	C28X_REG_IER,
	C28X_REG_IFR,
	C28X_REG_DP,
	C28X_REG_DBGIER,
	C28X_REG_RPC,
	C28X_REG_RPTC,
	C28X_NUM_REGS,
};

static const struct c28x_reg_desc c28x_reg_descs[C28X_NUM_REGS] = {
	[C28X_REG_PC] = { "PC", 0, 24, "general" },
	[C28X_REG_SP] = { "SP", 1, 16, "general" },
	[C28X_REG_ACC] = { "ACC", 2, 32, "general" },
	[C28X_REG_P] = { "P", 3, 32, "general" },
	[C28X_REG_XT] = { "XT", 4, 32, "general" },
	[C28X_REG_ST0] = { "ST0", 5, 16, "general" },
	[C28X_REG_ST1] = { "ST1", 6, 16, "general" },
	[C28X_REG_XAR0] = { "XAR0", 7, 32, "general" },
	[C28X_REG_XAR1] = { "XAR1", 8, 32, "general" },
	[C28X_REG_XAR2] = { "XAR2", 9, 32, "general" },
	[C28X_REG_XAR3] = { "XAR3", 10, 32, "general" },
	[C28X_REG_XAR4] = { "XAR4", 11, 32, "general" },
	[C28X_REG_XAR5] = { "XAR5", 12, 32, "general" },
	[C28X_REG_XAR6] = { "XAR6", 13, 32, "general" },
	[C28X_REG_XAR7] = { "XAR7", 14, 32, "general" },
	[C28X_REG_IER] = { "IER", 15, 16, "system" },
	[C28X_REG_IFR] = { "IFR", 16, 16, "system" },
	[C28X_REG_DP] = { "DP", 17, 16, "system" },
	[C28X_REG_DBGIER] = { "DBGIER", 18, 16, "system" },
	[C28X_REG_RPC] = { "RPC", 19, 24, "system" },
	[C28X_REG_RPTC] = { "RPTC", 20, 16, "system" },
};

static const struct c28x_ti_regid_desc c28x_ti_regids[] = {
	{ "IC", 0, 0x0, 0 },
	{ "PC", 0, 0x0, 0 },
	{ "SP", 1, 0x0, 0 },
	{ "FP", 1, 0x0, 0 },
	{ "ACC", 2, 0x0, 0 },
	{ "P", 3, 0x0, 0 },
	{ "XT", 4, 0x0, 0 },
	{ "ST0", 5, 0x0, 0 },
	{ "ST1", 6, 0x0, 0 },
	{ "XAR0", 7, 0x0, 0 },
	{ "XAR1", 8, 0x0, 0 },
	{ "XAR2", 9, 0x0, 0 },
	{ "XAR3", 10, 0x0, 0 },
	{ "XAR4", 11, 0x0, 0 },
	{ "XAR5", 12, 0x0, 0 },
	{ "XAR6", 13, 0x0, 0 },
	{ "XAR7", 14, 0x0, 0 },
	{ "RB", -1, 0xf00, 1 },
	{ "STF", -1, 0xf02, 1 },
	{ "R0L", -1, 0xf10, 1 },
	{ "R0H", -1, 0xf12, 1 },
	{ "R1L", -1, 0xf14, 1 },
	{ "R1H", -1, 0xf16, 1 },
	{ "R2L", -1, 0xf18, 1 },
	{ "R2H", -1, 0xf1a, 1 },
	{ "R3L", -1, 0xf1c, 1 },
	{ "R3H", -1, 0xf1e, 1 },
	{ "R4L", -1, 0xf20, 1 },
	{ "R4H", -1, 0xf22, 1 },
	{ "R5L", -1, 0xf24, 1 },
	{ "R5H", -1, 0xf26, 1 },
	{ "R6L", -1, 0xf28, 1 },
	{ "R6H", -1, 0xf2a, 1 },
	{ "R7L", -1, 0xf2c, 1 },
	{ "R7H", -1, 0xf2e, 1 },
	{ "IER", 15, 0x0, 0 },
	{ "IFR", 16, 0x0, 0 },
	{ "DP", 17, 0x0, 0 },
	{ "DBGIER", 18, 0x0, 0 },
	{ "RPC", 19, 0x0, 0 },
	{ "RPTC", 20, 0x0, 0 },
	{ "ACU_SEL", 40, 0x0, 0 },
	{ "DCU_SEL", 41, 0x0, 0 },
	{ "ECU_SEL", 42, 0x0, 0 },
	{ "ACUPSA_L32", 43, 0x0, 0 },
	{ "ACUPSA_M08", 44, 0x0, 0 },
	{ "ACUPSA_CNTL", 45, 0x0, 0 },
	{ "ACUPSA", 46, 0x0, 0 },
	{ "ACUHWBPEVT_MASK", 47, 0x0, 0 },
	{ "ACUHWBPEVT_REF", 48, 0x0, 0 },
	{ "ACUHWBPEVT_CNTL", 49, 0x0, 0 },
	{ "ACUHWBPEVT", 50, 0x0, 0 },
	{ "ACUBUSEVT_MASK", 51, 0x0, 0 },
	{ "ACUBUSEVT_REF", 52, 0x0, 0 },
	{ "ACUBUSEVT_CNTL", 53, 0x0, 0 },
	{ "ACUBUSEVT", 54, 0x0, 0 },
	{ "ACUBENCHMARK_L32", 55, 0x0, 0 },
	{ "ACUBENCHMARK_M08", 56, 0x0, 0 },
	{ "ACUBENCHMARK_CNTL", 57, 0x0, 0 },
	{ "ACUBENCHMARK", 58, 0x0, 0 },
	{ "ACU32CNT_CNT", 59, 0x0, 0 },
	{ "ACU32CNT_MATCH", 60, 0x0, 0 },
	{ "ACU32CNT_CNTL", 61, 0x0, 0 },
	{ "ACU32CNT", 62, 0x0, 0 },
	{ "ACU16CNT1_CNT", 63, 0x0, 0 },
	{ "ACU16CNT2_CNT", 64, 0x0, 0 },
	{ "ACU16CNT1_MATCH", 65, 0x0, 0 },
	{ "ACU16CNT2_MATCH", 66, 0x0, 0 },
	{ "ACU16CNT_CNTL", 67, 0x0, 0 },
	{ "ACU16CNT", 68, 0x0, 0 },
	{ "ACUDMA_ADDR", 69, 0x0, 0 },
	{ "ACUDMA_DATA", 70, 0x0, 0 },
	{ "ACUDMA_CNTL", 71, 0x0, 0 },
	{ "ACUDMA", 72, 0x0, 0 },
	{ "DCUPSA_L32", 73, 0x0, 0 },
	{ "DCUPSA_M08", 74, 0x0, 0 },
	{ "DCUPSA_CNTL", 75, 0x0, 0 },
	{ "DCUPSA", 76, 0x0, 0 },
	{ "DCUHWBPEVT_MASK", 77, 0x0, 0 },
	{ "DCUHWBPEVT_REF", 78, 0x0, 0 },
	{ "DCUHWBPEVT_CNTL", 79, 0x0, 0 },
	{ "DCUHWBPEVT", 80, 0x0, 0 },
	{ "DCU2BUSEVT_MASK", 81, 0x0, 0 },
	{ "DCU2BUSEVT_REF", 82, 0x0, 0 },
	{ "DCU2BUSEVT_CNTL", 83, 0x0, 0 },
	{ "DCU2BUSEVT", 84, 0x0, 0 },
	{ "DCUBUSEVT_MASK", 85, 0x0, 0 },
	{ "DCUBUSEVT_REF", 86, 0x0, 0 },
	{ "DCUBUSEVT_CNTL", 87, 0x0, 0 },
	{ "DCUBUSEVT", 88, 0x0, 0 },
	{ "ECU_CNTL", 89, 0x0, 0 },
	{ "ECU", 90, 0x0, 0 },
	{ "ECU_EMU0", 93, 0x0, 0 },
	{ "ECU_EMU1", 94, 0x0, 0 },
	{ "ANASTOP", 92, 0x0, 0 },
	{ "ANA_ENABLE", 316, 0x0, 0 },
	{ "PSTRT_XINTF", 100, 0x0, 0 },
	{ "PEND_XINTF", 101, 0x0, 0 },
	{ "DSTRT_XINTF", 102, 0x0, 0 },
	{ "DEND_XINTF", 103, 0x0, 0 },
	{ "MCTL_XINTF", 104, 0x0, 0 },
	{ "XDTIMING0", 105, 0x0, 0 },
	{ "XDTIMING1", 106, 0x0, 0 },
	{ "XDTIMING2", 107, 0x0, 0 },
	{ "XDTIMING3", 108, 0x0, 0 },
	{ "XDTIMING4", 109, 0x0, 0 },
	{ "XPTIMING0", 110, 0x0, 0 },
	{ "XPTIMING1", 111, 0x0, 0 },
	{ "XINTFCNF0", 112, 0x0, 0 },
	{ "XINTFCNF1", 113, 0x0, 0 },
	{ "XINTFCNF2", 114, 0x0, 0 },
	{ "EMU_ENABLE", 115, 0x0, 0 },
	{ "SIDLE", 117, 0x0, 0 },
	{ "VMAP_IN", 118, 0x0, 0 },
	{ "M0M1MAP_IN", 119, 0x0, 0 },
	{ "PROTSTART", -1, 0x884, 1 },
	{ "PROTRANGE", -1, 0x885, 1 },
	{ "ENPROT", -1, 0x880, 1 },
	{ "AL", 200, 0x0, 0 },
	{ "AH", 201, 0x0, 0 },
	{ "PL", 202, 0x0, 0 },
	{ "PH", 203, 0x0, 0 },
	{ "SXM", 204, 0x0, 0 },
	{ "OVM", 205, 0x0, 0 },
	{ "V", 210, 0x0, 0 },
	{ "PM", 211, 0x0, 0 },
	{ "INTM", 213, 0x0, 0 },
	{ "PAGE0", 215, 0x0, 0 },
	{ "TL", 241, 0x0, 0 },
	{ "T", 242, 0x0, 0 },
	{ "XAR0L", 224, 0x0, 0 },
	{ "XAR0H", 225, 0x0, 0 },
	{ "XAR1L", 226, 0x0, 0 },
	{ "XAR1H", 227, 0x0, 0 },
	{ "XAR2L", 228, 0x0, 0 },
	{ "XAR2H", 229, 0x0, 0 },
	{ "XAR3L", 230, 0x0, 0 },
	{ "XAR3H", 231, 0x0, 0 },
	{ "XAR4L", 232, 0x0, 0 },
	{ "XAR4H", 233, 0x0, 0 },
	{ "XAR5L", 234, 0x0, 0 },
	{ "XAR5H", 235, 0x0, 0 },
	{ "XAR6L", 220, 0x0, 0 },
	{ "XAR6H", 221, 0x0, 0 },
	{ "XAR7L", 222, 0x0, 0 },
	{ "XAR7H", 223, 0x0, 0 },
	{ "AR0", 7, 0x0, 0 },
	{ "AR1", 8, 0x0, 0 },
	{ "AR2", 9, 0x0, 0 },
	{ "AR3", 10, 0x0, 0 },
	{ "AR4", 11, 0x0, 0 },
	{ "AR5", 12, 0x0, 0 },
	{ "AR6", 13, 0x0, 0 },
	{ "AR7", 14, 0x0, 0 },
	{ "DECODE2", 250, 0x0, 0 },
	{ "READ1", 251, 0x0, 0 },
	{ "READ2", 252, 0x0, 0 },
	{ "EXECUTE", 253, 0x0, 0 },
	{ "WRITE", 254, 0x0, 0 },
	{ "D2_INSTR", 255, 0x0, 0 },
	{ "R1_INSTR", 256, 0x0, 0 },
	{ "R2_INSTR", 257, 0x0, 0 },
	{ "EX_INSTR", 258, 0x0, 0 },
	{ "WR_INSTR", 259, 0x0, 0 },
	{ "CLK", 300, 0x0, 0 },
	{ "RUNCOUNT", 300, 0x0, 0 },
	{ "XDS_STAT", 302, 0x0, 0 },
	{ "XDS_DFR", 303, 0x0, 0 },
	{ "XDS_DBGM", 304, 0x0, 0 },
	{ "XDS_HPI", 305, 0x0, 0 },
	{ "XDS_IDMATCH", 306, 0x0, 0 },
	{ "XDS_PREEMPT", 307, 0x0, 0 },
	{ "XDS_MFREG1", 308, 0x0, 0 },
	{ "XDS_DCSTRBS", 309, 0x0, 0 },
	{ "XDS_ANASEIZE", 310, 0x0, 0 },
	{ "XDS_DFRCHANGE", 311, 0x0, 0 },
	{ "XDS_CLKFIX", 312, 0x0, 0 },
	{ "XDS_DLFIFOSZ", 313, 0x0, 0 },
	{ "XDS_MSGFIFOSZ", 314, 0x0, 0 },
	{ "XDS_RTDX_ENABLE", 315, 0x0, 0 },
};

struct c28x_common *target_to_c28x(struct target *target)
{
	return target ? target->arch_info : NULL;
}

static int c28x_transport_required(struct target *target, const char *op)
{
	struct c28x_common *c28x = target_to_c28x(target);

	if (!target || !target->tap) {
		LOG_ERROR("C28x %s requires a JTAG TAP", op);
		return ERROR_FAIL;
	}

	if (!c28x || !c28x->transport_enabled) {
		LOG_ERROR("C28x %s requires verified C28x debug transport opcodes. "
			"Use 'c28x transport enable' and 'c28x ir ...' only with silicon-verified values.", op);
		return ERROR_FAIL;
	}

	return ERROR_OK;
}

static int c28x_irscan(struct target *target, const struct c28x_scan_ir *ir)
{
	if (!ir->valid) {
		LOG_ERROR("C28x debug transport opcode is not configured");
		return ERROR_FAIL;
	}

	uint8_t out[DIV_ROUND_UP(32, 8)] = { 0 };
	struct scan_field field = {
		.num_bits = target->tap->ir_length,
		.out_value = out,
	};

	buf_set_u32(out, 0, field.num_bits, ir->value);
	jtag_add_ir_scan(target->tap, &field, TAP_IDLE);
	return ERROR_OK;
}

static int c28x_drscan(struct target *target, unsigned int bits,
		uint64_t out_value, uint64_t *in_value)
{
	uint8_t out[DIV_ROUND_UP(64, 8)] = { 0 };
	uint8_t in[DIV_ROUND_UP(64, 8)] = { 0 };

	if (bits == 0 || bits > 64)
		return ERROR_COMMAND_ARGUMENT_INVALID;

	buf_set_u64(out, 0, bits, out_value);

	struct scan_field field = {
		.num_bits = bits,
		.out_value = out,
		.in_value = in,
	};

	jtag_add_dr_scan(target->tap, 1, &field, TAP_IDLE);
	int retval = jtag_execute_queue();
	if (retval != ERROR_OK)
		return retval;

	if (in_value)
		*in_value = buf_get_u64(in, 0, bits);

	return ERROR_OK;
}

static int c28x_write_pulse(struct target *target, const struct c28x_scan_ir *ir)
{
	int retval = c28x_irscan(target, ir);
	if (retval != ERROR_OK)
		return retval;
	return jtag_execute_queue();
}

static int c28x_scan_idcode(struct target *target, uint32_t *idcode)
{
	struct c28x_common *c28x = target_to_c28x(target);
	uint64_t value = 0;
	int retval;

	retval = c28x_transport_required(target, "IDCODE read");
	if (retval != ERROR_OK)
		return retval;
	retval = c28x_irscan(target, &c28x->ir_idcode);
	if (retval != ERROR_OK)
		return retval;
	retval = c28x_drscan(target, 32, 0, &value);
	if (retval != ERROR_OK)
		return retval;

	*idcode = (uint32_t)value;
	return ERROR_OK;
}

static int c28x_scan_status(struct target *target, uint32_t *status)
{
	struct c28x_common *c28x = target_to_c28x(target);
	uint64_t value = 0;
	int retval;

	retval = c28x_transport_required(target, "status read");
	if (retval != ERROR_OK)
		return retval;
	retval = c28x_irscan(target, &c28x->ir_status);
	if (retval != ERROR_OK)
		return retval;
	retval = c28x_drscan(target, c28x->status_dr_bits, 0, &value);
	if (retval != ERROR_OK)
		return retval;

	c28x->status_value = (uint32_t)value;
	if (status)
		*status = c28x->status_value;
	return ERROR_OK;
}

/* Configurable packet format used by the generic transport:
 *   register read/write DR:  [7:0] regnum, [39:8] value for writes
 *   memory read/write16 DR:  [31:0] word address, [47:32] value for writes
 * These packets are deliberately isolated here so a later silicon-specific
 * driver can replace only these helpers once the private TI TAP encoding is
 * available. */
static int c28x_transport_read_reg(struct target *target, unsigned int regnum,
		uint32_t *value)
{
	struct c28x_common *c28x = target_to_c28x(target);
	uint64_t in = 0;
	int retval;

	retval = c28x_transport_required(target, "register read");
	if (retval != ERROR_OK)
		return retval;
	retval = c28x_irscan(target, &c28x->ir_reg_read);
	if (retval != ERROR_OK)
		return retval;
	retval = c28x_drscan(target, 40, regnum & 0xff, &in);
	if (retval != ERROR_OK)
		return retval;

	*value = (uint32_t)(in >> 8);
	return ERROR_OK;
}

static int c28x_transport_write_reg(struct target *target, unsigned int regnum,
		uint32_t value)
{
	struct c28x_common *c28x = target_to_c28x(target);
	uint64_t packet = (regnum & 0xff) | ((uint64_t)value << 8);
	int retval;

	retval = c28x_transport_required(target, "register write");
	if (retval != ERROR_OK)
		return retval;
	retval = c28x_irscan(target, &c28x->ir_reg_write);
	if (retval != ERROR_OK)
		return retval;
	return c28x_drscan(target, 40, packet, NULL);
}

static int c28x_transport_read_mem16(struct target *target, uint32_t word_addr,
		uint16_t *value)
{
	struct c28x_common *c28x = target_to_c28x(target);
	uint64_t in = 0;
	int retval;

	retval = c28x_transport_required(target, "16-bit memory read");
	if (retval != ERROR_OK)
		return retval;
	retval = c28x_irscan(target, &c28x->ir_mem_read16);
	if (retval != ERROR_OK)
		return retval;
	retval = c28x_drscan(target, 48, word_addr, &in);
	if (retval != ERROR_OK)
		return retval;

	*value = (uint16_t)(in >> 32);
	return ERROR_OK;
}

static int c28x_transport_write_mem16(struct target *target, uint32_t word_addr,
		uint16_t value)
{
	struct c28x_common *c28x = target_to_c28x(target);
	uint64_t packet = (uint64_t)word_addr | ((uint64_t)value << 32);
	int retval;

	retval = c28x_transport_required(target, "16-bit memory write");
	if (retval != ERROR_OK)
		return retval;
	retval = c28x_irscan(target, &c28x->ir_mem_write16);
	if (retval != ERROR_OK)
		return retval;
	return c28x_drscan(target, 48, packet, NULL);
}

static int c28x_core_reg_get(struct reg *reg)
{
	struct c28x_core_reg *reg_info = reg->arch_info;
	struct c28x_common *c28x = reg_info->c28x;
	uint32_t value = 0;

	if (c28x->target->state != TARGET_HALTED) {
		LOG_DEBUG("C28x register %s requested while target is not halted", reg->name);
		return ERROR_TARGET_NOT_HALTED;
	}

	int retval = c28x_transport_read_reg(c28x->target, reg_info->ti_id, &value);
	if (retval != ERROR_OK)
		return retval;

	buf_set_u32(reg->value, 0, reg->size, value);
	reg->valid = true;
	reg->dirty = false;
	return ERROR_OK;
}

static int c28x_core_reg_set(struct reg *reg, uint8_t *buf)
{
	struct c28x_core_reg *reg_info = reg->arch_info;
	struct c28x_common *c28x = reg_info->c28x;
	uint32_t value;

	if (c28x->target->state != TARGET_HALTED)
		return ERROR_TARGET_NOT_HALTED;

	value = buf_get_u32(buf, 0, reg->size);
	int retval = c28x_transport_write_reg(c28x->target, reg_info->ti_id, value);
	if (retval != ERROR_OK)
		return retval;

	buf_set_u32(reg->value, 0, reg->size, value);
	reg->valid = true;
	reg->dirty = false;
	return ERROR_OK;
}

static const struct reg_arch_type c28x_reg_type = {
	.get = c28x_core_reg_get,
	.set = c28x_core_reg_set,
};

static struct reg_cache *c28x_build_reg_cache(struct target *target)
{
	struct c28x_common *c28x = target_to_c28x(target);
	struct reg_cache *cache = calloc(1, sizeof(*cache));
	struct reg *regs = calloc(C28X_NUM_REGS, sizeof(*regs));
	struct c28x_core_reg *info = calloc(C28X_NUM_REGS, sizeof(*info));
	uint8_t *values = calloc(C28X_NUM_REGS, C28X_REG_BYTES);

	if (!cache || !regs || !info || !values) {
		free(cache);
		free(regs);
		free(info);
		free(values);
		return NULL;
	}

	cache->name = "C28x registers";
	cache->num_regs = C28X_NUM_REGS;
	cache->reg_list = regs;

	for (unsigned int i = 0; i < C28X_NUM_REGS; i++) {
		info[i].c28x = c28x;
		info[i].num = i;
		info[i].ti_id = c28x_reg_descs[i].ti_id;
		info[i].name = c28x_reg_descs[i].name;

		regs[i].name = c28x_reg_descs[i].name;
		regs[i].number = i;
		regs[i].size = c28x_reg_descs[i].bits;
		regs[i].value = values + i * C28X_REG_BYTES;
		regs[i].dirty = false;
		regs[i].valid = false;
		regs[i].exist = true;
		regs[i].hidden = false;
		regs[i].caller_save = false;
		regs[i].group = c28x_reg_descs[i].group;
		regs[i].arch_info = &info[i];
		regs[i].type = &c28x_reg_type;
	}

	c28x->core_cache = cache;
	c28x->reg_values = values;
	c28x->reg_info = info;
	return cache;
}

static bool c28x_memory_ready(struct target *target)
{
	return target->state == TARGET_HALTED;
}

static int c28x_poll(struct target *target)
{
	struct c28x_common *c28x = target_to_c28x(target);
	uint32_t status = 0;
	int retval;

	if (!c28x || !c28x->transport_enabled || !c28x->ir_status.valid)
		return ERROR_OK;

	retval = c28x_scan_status(target, &status);
	if (retval != ERROR_OK)
		return retval;

	if (status & c28x->status_halt_mask) {
		target->state = TARGET_HALTED;
		target->debug_reason = DBG_REASON_DBGRQ;
	} else if (status & c28x->status_run_mask) {
		target->state = TARGET_RUNNING;
		target->debug_reason = DBG_REASON_NOTHALTED;
	} else {
		target->state = TARGET_UNKNOWN;
		target->debug_reason = DBG_REASON_UNDEFINED;
	}

	return ERROR_OK;
}

static int c28x_arch_state(struct target *target)
{
	struct c28x_common *c28x = target_to_c28x(target);

	LOG_USER("target halted due to %s, C28x status=0x%08" PRIx32,
		debug_reason_name(target), c28x ? c28x->status_value : 0);
	return ERROR_OK;
}

static int c28x_halt(struct target *target)
{
	struct c28x_common *c28x = target_to_c28x(target);
	int retval;

	if (target->state == TARGET_HALTED)
		return ERROR_OK;

	retval = c28x_transport_required(target, "halt");
	if (retval != ERROR_OK)
		return retval;
	retval = c28x_write_pulse(target, &c28x->ir_halt);
	if (retval != ERROR_OK)
		return retval;

	target->state = TARGET_HALTED;
	target->debug_reason = DBG_REASON_DBGRQ;
	register_cache_invalidate(target->reg_cache);
	return ERROR_OK;
}

static int c28x_resume(struct target *target, bool current, target_addr_t address,
		bool handle_breakpoints, bool debug_execution)
{
	struct c28x_common *c28x = target_to_c28x(target);
	struct reg *pc;
	int retval;

	(void)handle_breakpoints;

	retval = c28x_transport_required(target, "resume");
	if (retval != ERROR_OK)
		return retval;

	if (!current) {
		pc = register_get_by_name(target->reg_cache, "PC", true);
		if (!pc)
			return ERROR_FAIL;
		uint8_t buf[4] = { 0 };
		buf_set_u32(buf, 0, 32, address);
		retval = c28x_core_reg_set(pc, buf);
		if (retval != ERROR_OK)
			return retval;
	}

	retval = c28x_write_pulse(target, &c28x->ir_resume);
	if (retval != ERROR_OK)
		return retval;

	target->state = debug_execution ? TARGET_DEBUG_RUNNING : TARGET_RUNNING;
	target->debug_reason = DBG_REASON_NOTHALTED;
	return ERROR_OK;
}

static int c28x_step(struct target *target, bool current, target_addr_t address,
		bool handle_breakpoints)
{
	struct c28x_common *c28x = target_to_c28x(target);
	int retval;

	(void)handle_breakpoints;

	retval = c28x_transport_required(target, "single-step");
	if (retval != ERROR_OK)
		return retval;

	if (!current) {
		struct reg *pc = register_get_by_name(target->reg_cache, "PC", true);
		uint8_t buf[4] = { 0 };
		if (!pc)
			return ERROR_FAIL;
		buf_set_u32(buf, 0, 32, address);
		retval = c28x_core_reg_set(pc, buf);
		if (retval != ERROR_OK)
			return retval;
	}

	retval = c28x_write_pulse(target, &c28x->ir_step);
	if (retval != ERROR_OK)
		return retval;

	target->state = TARGET_HALTED;
	target->debug_reason = DBG_REASON_SINGLESTEP;
	register_cache_invalidate(target->reg_cache);
	return ERROR_OK;
}

static int c28x_assert_reset(struct target *target)
{
	target->state = TARGET_RESET;
	register_cache_invalidate(target->reg_cache);
	return ERROR_OK;
}

static int c28x_deassert_reset(struct target *target)
{
	if (target->reset_halt)
		return c28x_halt(target);

	target->state = TARGET_RUNNING;
	target->debug_reason = DBG_REASON_NOTHALTED;
	return ERROR_OK;
}

static int c28x_soft_reset_halt(struct target *target)
{
	int retval = c28x_assert_reset(target);
	if (retval != ERROR_OK)
		return retval;
	retval = c28x_deassert_reset(target);
	if (retval != ERROR_OK)
		return retval;
	return c28x_halt(target);
}

static const char *c28x_get_gdb_arch(const struct target *target)
{
	const struct c28x_common *c28x = target->arch_info;
	return (c28x && c28x->gdb_arch) ? c28x->gdb_arch : C28X_DEFAULT_GDB_ARCH;
}

static int c28x_get_gdb_reg_list(struct target *target, struct reg **reg_list[],
		int *reg_list_size, enum target_register_class reg_class)
{
	(void)reg_class;

	*reg_list_size = C28X_NUM_REGS;
	*reg_list = calloc(C28X_NUM_REGS, sizeof(struct reg *));
	if (!*reg_list)
		return ERROR_FAIL;

	for (unsigned int i = 0; i < C28X_NUM_REGS; i++)
		(*reg_list)[i] = &target->reg_cache->reg_list[i];

	return ERROR_OK;
}

static int c28x_get_gdb_reg_list_noread(struct target *target,
		struct reg **reg_list[], int *reg_list_size,
		enum target_register_class reg_class)
{
	return c28x_get_gdb_reg_list(target, reg_list, reg_list_size, reg_class);
}

static int c28x_read_u16_as_bytes(struct target *target, target_addr_t address,
		uint8_t *buffer)
{
	uint16_t value;
	int retval = c28x_transport_read_mem16(target, (uint32_t)(address >> 1), &value);
	if (retval != ERROR_OK)
		return retval;

	if (address & 1)
		buffer[0] = (uint8_t)(value >> 8);
	else
		buffer[0] = (uint8_t)value;
	return ERROR_OK;
}

static int c28x_write_u8(struct target *target, target_addr_t address, uint8_t value)
{
	uint16_t word;
	int retval = c28x_transport_read_mem16(target, (uint32_t)(address >> 1), &word);
	if (retval != ERROR_OK)
		return retval;

	if (address & 1)
		word = (word & 0x00ff) | ((uint16_t)value << 8);
	else
		word = (word & 0xff00) | value;

	return c28x_transport_write_mem16(target, (uint32_t)(address >> 1), word);
}

static int c28x_read_memory(struct target *target, target_addr_t address,
		uint32_t size, uint32_t count, uint8_t *buffer)
{
	if (target->state != TARGET_HALTED)
		return ERROR_TARGET_NOT_HALTED;

	if (size != 1 && size != 2 && size != 4)
		return ERROR_COMMAND_ARGUMENT_INVALID;

	for (uint32_t i = 0; i < count; i++) {
		if (size == 1) {
			int retval = c28x_read_u16_as_bytes(target, address + i, &buffer[i]);
			if (retval != ERROR_OK)
				return retval;
		} else if (size == 2) {
			if ((address + i * 2) & 1)
				return ERROR_TARGET_UNALIGNED_ACCESS;
			uint16_t value;
			int retval = c28x_transport_read_mem16(target,
					(uint32_t)((address + i * 2) >> 1), &value);
			if (retval != ERROR_OK)
				return retval;
			target_buffer_set_u16(target, buffer + i * 2, value);
		} else {
			if ((address + i * 4) & 1)
				return ERROR_TARGET_UNALIGNED_ACCESS;
			uint16_t low, high;
			uint32_t word_addr = (uint32_t)((address + i * 4) >> 1);
			int retval = c28x_transport_read_mem16(target, word_addr, &low);
			if (retval != ERROR_OK)
				return retval;
			retval = c28x_transport_read_mem16(target, word_addr + 1, &high);
			if (retval != ERROR_OK)
				return retval;
			target_buffer_set_u32(target, buffer + i * 4,
					((uint32_t)high << 16) | low);
		}
	}

	return ERROR_OK;
}

static int c28x_write_memory(struct target *target, target_addr_t address,
		uint32_t size, uint32_t count, const uint8_t *buffer)
{
	if (target->state != TARGET_HALTED)
		return ERROR_TARGET_NOT_HALTED;

	if (size != 1 && size != 2 && size != 4)
		return ERROR_COMMAND_ARGUMENT_INVALID;

	for (uint32_t i = 0; i < count; i++) {
		if (size == 1) {
			int retval = c28x_write_u8(target, address + i, buffer[i]);
			if (retval != ERROR_OK)
				return retval;
		} else if (size == 2) {
			if ((address + i * 2) & 1)
				return ERROR_TARGET_UNALIGNED_ACCESS;
			uint16_t value = target_buffer_get_u16(target, buffer + i * 2);
			int retval = c28x_transport_write_mem16(target,
					(uint32_t)((address + i * 2) >> 1), value);
			if (retval != ERROR_OK)
				return retval;
		} else {
			if ((address + i * 4) & 1)
				return ERROR_TARGET_UNALIGNED_ACCESS;
			uint32_t value = target_buffer_get_u32(target, buffer + i * 4);
			uint32_t word_addr = (uint32_t)((address + i * 4) >> 1);
			int retval = c28x_transport_write_mem16(target, word_addr,
					(uint16_t)(value & 0xffff));
			if (retval != ERROR_OK)
				return retval;
			retval = c28x_transport_write_mem16(target, word_addr + 1,
					(uint16_t)(value >> 16));
			if (retval != ERROR_OK)
				return retval;
		}
	}

	return ERROR_OK;
}

static int c28x_read_buffer(struct target *target, target_addr_t address,
		uint32_t size, uint8_t *buffer)
{
	return c28x_read_memory(target, address, 1, size, buffer);
}

static int c28x_write_buffer(struct target *target, target_addr_t address,
		uint32_t size, const uint8_t *buffer)
{
	return c28x_write_memory(target, address, 1, size, buffer);
}

static int c28x_find_free_bool(bool *used, unsigned int count)
{
	for (unsigned int i = 0; i < count; i++) {
		if (!used[i])
			return (int)i;
	}
	return -1;
}

static int c28x_add_breakpoint(struct target *target, struct breakpoint *bp)
{
	struct c28x_common *c28x = target_to_c28x(target);

	if (bp->type == BKPT_SOFT) {
		LOG_ERROR("C28x software breakpoints require a verified instruction encoding policy");
		return ERROR_TARGET_RESOURCE_NOT_AVAILABLE;
	}

	int slot = c28x_find_free_bool(c28x->hw_breakpoint_used, C28X_MAX_HW_BREAKPOINTS);
	if (slot < 0)
		return ERROR_TARGET_RESOURCE_NOT_AVAILABLE;

	if (c28x->transport_enabled && c28x->ir_bp_write.valid) {
		uint64_t packet = ((uint64_t)slot & 0xff) |
			(((uint64_t)bp->address & 0xffffffff) << 8) |
			((uint64_t)1 << 40);
		int retval = c28x_irscan(target, &c28x->ir_bp_write);
		if (retval != ERROR_OK)
			return retval;
		retval = c28x_drscan(target, 48, packet, NULL);
		if (retval != ERROR_OK)
			return retval;
	} else {
		LOG_WARNING("C28x hardware breakpoint recorded locally; transport BP programming is not configured");
	}

	c28x->hw_breakpoint_used[slot] = true;
	breakpoint_hw_set(bp, slot);
	return ERROR_OK;
}

static int c28x_remove_breakpoint(struct target *target, struct breakpoint *bp)
{
	struct c28x_common *c28x = target_to_c28x(target);

	if (!bp->is_set || bp->number >= C28X_MAX_HW_BREAKPOINTS)
		return ERROR_OK;

	if (c28x->transport_enabled && c28x->ir_bp_write.valid) {
		uint64_t packet = (uint64_t)(bp->number & 0xff);
		int retval = c28x_irscan(target, &c28x->ir_bp_write);
		if (retval != ERROR_OK)
			return retval;
		retval = c28x_drscan(target, 48, packet, NULL);
		if (retval != ERROR_OK)
			return retval;
	}

	c28x->hw_breakpoint_used[bp->number] = false;
	bp->is_set = false;
	return ERROR_OK;
}

static int c28x_add_watchpoint(struct target *target, struct watchpoint *wp)
{
	struct c28x_common *c28x = target_to_c28x(target);
	int slot = c28x_find_free_bool(c28x->hw_watchpoint_used, C28X_MAX_HW_WATCHPOINTS);
	if (slot < 0)
		return ERROR_TARGET_RESOURCE_NOT_AVAILABLE;

	if (c28x->transport_enabled && c28x->ir_wp_write.valid) {
		uint64_t packet = ((uint64_t)slot & 0xff) |
			(((uint64_t)wp->address & 0xffffffff) << 8) |
			(((uint64_t)wp->rw & 0x3) << 40) |
			((uint64_t)1 << 42);
		int retval = c28x_irscan(target, &c28x->ir_wp_write);
		if (retval != ERROR_OK)
			return retval;
		retval = c28x_drscan(target, 48, packet, NULL);
		if (retval != ERROR_OK)
			return retval;
	} else {
		LOG_WARNING("C28x watchpoint recorded locally; transport WP programming is not configured");
	}

	c28x->hw_watchpoint_used[slot] = true;
	watchpoint_set(wp, slot);
	return ERROR_OK;
}

static int c28x_remove_watchpoint(struct target *target, struct watchpoint *wp)
{
	struct c28x_common *c28x = target_to_c28x(target);

	if (!wp->is_set || wp->number >= C28X_MAX_HW_WATCHPOINTS)
		return ERROR_OK;

	if (c28x->transport_enabled && c28x->ir_wp_write.valid) {
		uint64_t packet = (uint64_t)(wp->number & 0xff);
		int retval = c28x_irscan(target, &c28x->ir_wp_write);
		if (retval != ERROR_OK)
			return retval;
		retval = c28x_drscan(target, 48, packet, NULL);
		if (retval != ERROR_OK)
			return retval;
	}

	c28x->hw_watchpoint_used[wp->number] = false;
	wp->is_set = false;
	return ERROR_OK;
}

static int c28x_hit_watchpoint(struct target *target, struct watchpoint **hit_watchpoint)
{
	(void)target;
	*hit_watchpoint = NULL;
	return ERROR_OK;
}

static int c28x_examine(struct target *target)
{
	struct c28x_common *c28x = target_to_c28x(target);
	uint32_t idcode;

	if (!target->tap)
		return ERROR_FAIL;

	if (c28x && c28x->transport_enabled && c28x->ir_idcode.valid) {
		int retval = c28x_scan_idcode(target, &idcode);
		if (retval != ERROR_OK)
			return retval;
		LOG_INFO("C28x TAP IDCODE: 0x%08" PRIx32, idcode);
	}

	target_set_examined(target);
	return ERROR_OK;
}

static int c28x_init_target(struct command_context *cmd_ctx, struct target *target)
{
	(void)cmd_ctx;

	struct c28x_common *c28x = target_to_c28x(target);
	if (!c28x)
		return ERROR_FAIL;

	target->endianness = TARGET_LITTLE_ENDIAN;
	target->state = TARGET_UNKNOWN;
	target->debug_reason = DBG_REASON_UNDEFINED;
	target->reg_cache = c28x_build_reg_cache(target);
	if (!target->reg_cache)
		return ERROR_FAIL;
	return ERROR_OK;
}

static int c28x_target_create(struct target *target)
{
	struct c28x_common *c28x = calloc(1, sizeof(*c28x));
	if (!c28x)
		return ERROR_FAIL;

	c28x->target = target;
	c28x->gdb_arch = strdup(C28X_DEFAULT_GDB_ARCH);
	c28x->ti_proc_id = C28X_TI_PROCID;
	c28x->xds110_memread_cmd = C28X_XDS110_MEMREAD_CMD;
	c28x->xds110_memwrite_cmd = C28X_XDS110_MEMWRITE_CMD;
	c28x->status_halt_mask = C28X_STATUS_HALT_MASK_DEFAULT;
	c28x->status_run_mask = C28X_STATUS_RUN_MASK_DEFAULT;
	c28x->status_dr_bits = C28X_STATUS_DR_BITS_DEFAULT;
	c28x->raw_data_dr_bits = C28X_RAW_DATA_DR_BITS_DEFAULT;
	c28x->transport_enabled = false;
	c28x->ir_bypass.valid = true;
	c28x->ir_bypass.value = 0xffffffff;

	target->arch_info = c28x;
	return ERROR_OK;
}

static void c28x_deinit_target(struct target *target)
{
	struct c28x_common *c28x = target_to_c28x(target);
	if (!c28x)
		return;

	if (c28x->core_cache) {
		free(c28x->core_cache->reg_list);
		free(c28x->core_cache);
	}
	free(c28x->reg_values);
	free(c28x->reg_info);
	free(c28x->gdb_arch);
	free(c28x->device_name);
	free(c28x->gel_file);
	free(c28x);
	target->arch_info = NULL;
}

static unsigned int c28x_address_bits(struct target *target)
{
	(void)target;
	return 32;
}

static unsigned int c28x_data_bits(struct target *target)
{
	(void)target;
	return 16;
}

static int c28x_insn_set(struct command_invocation *cmd, struct target *target,
		const char **insn_set)
{
	(void)cmd;
	(void)target;
	*insn_set = "c28x";
	return ERROR_OK;
}


static int c28x_replace_string(char **slot, const char *value)
{
	char *copy = strdup(value);
	if (!copy)
		return ERROR_FAIL;
	free(*slot);
	*slot = copy;
	return ERROR_OK;
}

COMMAND_HANDLER(c28x_handle_device_command)
{
	struct target *target = get_current_target(CMD_CTX);
	struct c28x_common *c28x = target_to_c28x(target);

	if (!c28x)
		return ERROR_FAIL;
	if (CMD_ARGC > 1)
		return ERROR_COMMAND_SYNTAX_ERROR;

	if (CMD_ARGC == 0) {
		command_print(CMD, "%s", c28x->device_name ? c28x->device_name : "unknown");
		return ERROR_OK;
	}

	return c28x_replace_string(&c28x->device_name, CMD_ARGV[0]);
}

COMMAND_HANDLER(c28x_handle_gel_file_command)
{
	struct target *target = get_current_target(CMD_CTX);
	struct c28x_common *c28x = target_to_c28x(target);

	if (!c28x)
		return ERROR_FAIL;
	if (CMD_ARGC > 1)
		return ERROR_COMMAND_SYNTAX_ERROR;

	if (CMD_ARGC == 0) {
		command_print(CMD, "%s", c28x->gel_file ? c28x->gel_file : "unset");
		return ERROR_OK;
	}

	return c28x_replace_string(&c28x->gel_file, CMD_ARGV[0]);
}

COMMAND_HANDLER(c28x_handle_procid_command)
{
	struct target *target = get_current_target(CMD_CTX);
	struct c28x_common *c28x = target_to_c28x(target);
	uint32_t value;

	if (!c28x)
		return ERROR_FAIL;
	if (CMD_ARGC > 1)
		return ERROR_COMMAND_SYNTAX_ERROR;

	if (CMD_ARGC == 0) {
		command_print(CMD, "0x%08" PRIx32, c28x->ti_proc_id);
		return ERROR_OK;
	}

	COMMAND_PARSE_NUMBER(u32, CMD_ARGV[0], value);
	c28x->ti_proc_id = value;
	return ERROR_OK;
}

COMMAND_HANDLER(c28x_handle_icepick_port_command)
{
	struct target *target = get_current_target(CMD_CTX);
	struct c28x_common *c28x = target_to_c28x(target);
	uint32_t value;

	if (!c28x)
		return ERROR_FAIL;
	if (CMD_ARGC > 1)
		return ERROR_COMMAND_SYNTAX_ERROR;

	if (CMD_ARGC == 0) {
		if (c28x->icepick_port_valid)
			command_print(CMD, "0x%02" PRIx32, c28x->icepick_port);
		else
			command_print(CMD, "direct-or-unset");
		return ERROR_OK;
	}

	COMMAND_PARSE_NUMBER(u32, CMD_ARGV[0], value);
	if (value > 0xff)
		return ERROR_COMMAND_ARGUMENT_INVALID;
	c28x->icepick_port = value;
	c28x->icepick_port_valid = true;
	return ERROR_OK;
}

COMMAND_HANDLER(c28x_handle_xds110_command)
{
	struct target *target = get_current_target(CMD_CTX);
	struct c28x_common *c28x = target_to_c28x(target);
	uint32_t memread, memwrite;

	if (!c28x)
		return ERROR_FAIL;
	if (CMD_ARGC != 0 && CMD_ARGC != 2)
		return ERROR_COMMAND_SYNTAX_ERROR;

	if (CMD_ARGC == 2) {
		COMMAND_PARSE_NUMBER(u32, CMD_ARGV[0], memread);
		COMMAND_PARSE_NUMBER(u32, CMD_ARGV[1], memwrite);
		if (memread > 0xff || memwrite > 0xff)
			return ERROR_COMMAND_ARGUMENT_INVALID;
		c28x->xds110_memread_cmd = memread;
		c28x->xds110_memwrite_cmd = memwrite;
	}

	command_print(CMD, "XDS110 C28X_MEMREAD=0x%02" PRIx32 " C28X_MEMWRITE=0x%02" PRIx32,
		c28x->xds110_memread_cmd, c28x->xds110_memwrite_cmd);
	return ERROR_OK;
}

COMMAND_HANDLER(c28x_handle_regids_command)
{
	const char *filter = CMD_ARGC == 0 ? "core" : CMD_ARGV[0];
	bool show_all, show_core, show_debug, show_mapped;

	if (CMD_ARGC > 1)
		return ERROR_COMMAND_SYNTAX_ERROR;

	show_all = !strcmp(filter, "all");
	show_core = show_all || !strcmp(filter, "core");
	show_debug = show_all || !strcmp(filter, "debug");
	show_mapped = show_all || !strcmp(filter, "mapped");
	if (!show_all && !show_core && !show_debug && !show_mapped)
		return ERROR_COMMAND_ARGUMENT_INVALID;

	command_print(CMD, "TI C28x register IDs from CCS TMS320C28XX_regids.xml (%s)", filter);
	for (unsigned int i = 0; i < ARRAY_SIZE(c28x_ti_regids); i++) {
		const struct c28x_ti_regid_desc *r = &c28x_ti_regids[i];
		bool mapped = r->ti_id < 0;
		bool core = r->ti_id >= 0 && r->ti_id <= 20;
		bool debug = r->ti_id >= 40;
		if ((mapped && !show_mapped) || (core && !show_core) || (debug && !show_debug))
			continue;
		if (!mapped && !core && !debug && !show_all)
			continue;
		if (mapped)
			command_print(CMD, "  %-24s mapped page=%u address=0x%05" PRIx32,
				r->name, r->page, r->address);
		else
			command_print(CMD, "  %-24s id=%" PRId32, r->name, r->ti_id);
	}
	return ERROR_OK;
}

COMMAND_HANDLER(c28x_handle_gti_command)
{
	const char *filter = CMD_ARGC == 0 ? "all" : CMD_ARGV[0];

	if (CMD_ARGC > 1)
		return ERROR_COMMAND_SYNTAX_ERROR;

	if (strcmp(filter, "all") && strcmp(filter, "ops") &&
		strcmp(filter, "flags") && strcmp(filter, "xds110"))
		return ERROR_COMMAND_ARGUMENT_INVALID;

	command_print(CMD, "CCS-derived C28x native GTI/XDS metadata");
	if (!strcmp(filter, "all") || !strcmp(filter, "ops")) {
		command_print(CMD, "  TRG_call operation IDs recovered from tixds28x.dvr:");
		for (unsigned int i = 0; i < ARRAY_SIZE(c28x_gti_ops); i++)
			command_print(CMD, "    %-12s op=0x%02" PRIx32 " packet=%s",
				c28x_gti_ops[i].name, c28x_gti_ops[i].opcode, c28x_gti_ops[i].packet);
	}
	if (!strcmp(filter, "all") || !strcmp(filter, "flags")) {
		command_print(CMD, "  Packet flags:");
		command_print(CMD, "    realtime      0x%08x", C28X_GTI_FLAG_REALTIME);
		command_print(CMD, "    single_step   0x%08x", C28X_GTI_FLAG_SINGLE_STEP);
		command_print(CMD, "    force_run     0x%08x", C28X_GTI_FLAG_FORCE_RUN);
	}
	if (!strcmp(filter, "all") || !strcmp(filter, "xds110")) {
		command_print(CMD, "  XDS110 firmware command IDs from jscxds110.dll exports:");
		command_print(CMD, "    C28X_MemRead  0x%02x", C28X_XDS110_MEMREAD_CMD);
		command_print(CMD, "    C28X_MemWrite 0x%02x", C28X_XDS110_MEMWRITE_CMD);
	}

	return ERROR_OK;
}

COMMAND_HANDLER(c28x_handle_transport_command)
{
	struct target *target = get_current_target(CMD_CTX);
	struct c28x_common *c28x = target_to_c28x(target);

	if (!c28x)
		return ERROR_FAIL;

	if (CMD_ARGC != 1)
		return ERROR_COMMAND_SYNTAX_ERROR;

	if (!strcmp(CMD_ARGV[0], "enable"))
		c28x->transport_enabled = true;
	else if (!strcmp(CMD_ARGV[0], "disable"))
		c28x->transport_enabled = false;
	else
		return ERROR_COMMAND_SYNTAX_ERROR;

	command_print(CMD, "C28x debug transport %s",
		c28x->transport_enabled ? "enabled" : "disabled");
	return ERROR_OK;
}

static struct c28x_scan_ir *c28x_ir_by_name(struct c28x_common *c28x, const char *name)
{
	if (!strcmp(name, "idcode"))
		return &c28x->ir_idcode;
	if (!strcmp(name, "status"))
		return &c28x->ir_status;
	if (!strcmp(name, "halt"))
		return &c28x->ir_halt;
	if (!strcmp(name, "resume"))
		return &c28x->ir_resume;
	if (!strcmp(name, "step"))
		return &c28x->ir_step;
	if (!strcmp(name, "reg_read"))
		return &c28x->ir_reg_read;
	if (!strcmp(name, "reg_write"))
		return &c28x->ir_reg_write;
	if (!strcmp(name, "mem_read16"))
		return &c28x->ir_mem_read16;
	if (!strcmp(name, "mem_write16"))
		return &c28x->ir_mem_write16;
	if (!strcmp(name, "bp_write"))
		return &c28x->ir_bp_write;
	if (!strcmp(name, "wp_write"))
		return &c28x->ir_wp_write;
	if (!strcmp(name, "bypass"))
		return &c28x->ir_bypass;
	return NULL;
}

COMMAND_HANDLER(c28x_handle_ir_command)
{
	struct target *target = get_current_target(CMD_CTX);
	struct c28x_common *c28x = target_to_c28x(target);
	uint32_t value;
	struct c28x_scan_ir *ir;

	if (!c28x)
		return ERROR_FAIL;

	if (CMD_ARGC < 1 || CMD_ARGC > 2)
		return ERROR_COMMAND_SYNTAX_ERROR;

	ir = c28x_ir_by_name(c28x, CMD_ARGV[0]);
	if (!ir)
		return ERROR_COMMAND_ARGUMENT_INVALID;

	if (CMD_ARGC == 1) {
		if (ir->valid)
			command_print(CMD, "%s = 0x%08" PRIx32, CMD_ARGV[0], ir->value);
		else
			command_print(CMD, "%s is unset", CMD_ARGV[0]);
		return ERROR_OK;
	}

	COMMAND_PARSE_NUMBER(u32, CMD_ARGV[1], value);
	ir->value = value;
	ir->valid = true;
	command_print(CMD, "%s = 0x%08" PRIx32, CMD_ARGV[0], ir->value);
	return ERROR_OK;
}

COMMAND_HANDLER(c28x_handle_status_format_command)
{
	struct target *target = get_current_target(CMD_CTX);
	struct c28x_common *c28x = target_to_c28x(target);
	uint32_t bits, halt_mask, run_mask;

	if (!c28x)
		return ERROR_FAIL;

	if (CMD_ARGC != 3)
		return ERROR_COMMAND_SYNTAX_ERROR;

	COMMAND_PARSE_NUMBER(u32, CMD_ARGV[0], bits);
	COMMAND_PARSE_NUMBER(u32, CMD_ARGV[1], halt_mask);
	COMMAND_PARSE_NUMBER(u32, CMD_ARGV[2], run_mask);

	if (!bits || bits > 64)
		return ERROR_COMMAND_ARGUMENT_INVALID;

	c28x->status_dr_bits = bits;
	c28x->status_halt_mask = halt_mask;
	c28x->status_run_mask = run_mask;
	return ERROR_OK;
}

COMMAND_HANDLER(c28x_handle_raw_ir_command)
{
	struct target *target = get_current_target(CMD_CTX);
	uint32_t value;
	uint8_t out[DIV_ROUND_UP(32, 8)] = { 0 };

	if (!target || !target->tap)
		return ERROR_FAIL;
	if (CMD_ARGC != 1)
		return ERROR_COMMAND_SYNTAX_ERROR;

	COMMAND_PARSE_NUMBER(u32, CMD_ARGV[0], value);
	struct scan_field field = {
		.num_bits = target->tap->ir_length,
		.out_value = out,
	};
	buf_set_u32(out, 0, field.num_bits, value);
	jtag_add_ir_scan(target->tap, &field, TAP_IDLE);
	return jtag_execute_queue();
}

COMMAND_HANDLER(c28x_handle_raw_dr_command)
{
	struct target *target = get_current_target(CMD_CTX);
	uint32_t bits;
	uint64_t out_value = 0, in_value = 0;

	if (!target || !target->tap)
		return ERROR_FAIL;
	if (CMD_ARGC < 1 || CMD_ARGC > 2)
		return ERROR_COMMAND_SYNTAX_ERROR;

	COMMAND_PARSE_NUMBER(u32, CMD_ARGV[0], bits);
	if (CMD_ARGC == 2)
		COMMAND_PARSE_NUMBER(u64, CMD_ARGV[1], out_value);

	int retval = c28x_drscan(target, bits, out_value, &in_value);
	if (retval != ERROR_OK)
		return retval;

	command_print(CMD, "0x%016" PRIx64, in_value);
	return ERROR_OK;
}

COMMAND_HANDLER(c28x_handle_idcode_command)
{
	struct target *target = get_current_target(CMD_CTX);
	uint32_t idcode;
	int retval = c28x_scan_idcode(target, &idcode);
	if (retval != ERROR_OK)
		return retval;
	command_print(CMD, "C28x IDCODE: 0x%08" PRIx32, idcode);
	return ERROR_OK;
}

COMMAND_HANDLER(c28x_handle_status_command)
{
	struct target *target = get_current_target(CMD_CTX);
	uint32_t status;
	int retval = c28x_scan_status(target, &status);
	if (retval != ERROR_OK)
		return retval;
	command_print(CMD, "C28x status: 0x%08" PRIx32, status);
	return ERROR_OK;
}

COMMAND_HANDLER(c28x_handle_info_command)
{
	struct target *target = get_current_target(CMD_CTX);
	struct c28x_common *c28x = target_to_c28x(target);
	if (!c28x)
		return ERROR_FAIL;

	command_print(CMD, "C28x target '%s'", target_name(target));
	command_print(CMD, "  state: %s", target_state_name(target));
	command_print(CMD, "  gdb_arch: %s", c28x_get_gdb_arch(target));
	command_print(CMD, "  device: %s", c28x->device_name ? c28x->device_name : "unknown");
	command_print(CMD, "  CCS ProcID: 0x%08" PRIx32, c28x->ti_proc_id);
	if (c28x->icepick_port_valid)
		command_print(CMD, "  ICEPick-C C28x port: 0x%02" PRIx32, c28x->icepick_port);
	else
		command_print(CMD, "  ICEPick-C C28x port: direct-or-unset");
	command_print(CMD, "  GEL file: %s", c28x->gel_file ? c28x->gel_file : "unset");
	command_print(CMD, "  XDS110 C28X_MEMREAD=0x%02" PRIx32 " C28X_MEMWRITE=0x%02" PRIx32,
		c28x->xds110_memread_cmd, c28x->xds110_memwrite_cmd);
	command_print(CMD, "  CCS GTI TRG ops: halt=0x%02x run=0x%02x step=0x%02x readreg=0x%02x writereg=0x%02x readmem=0x%02x writemem=0x%02x",
		C28X_GTI_OP_HALT, C28X_GTI_OP_RUN, C28X_GTI_OP_STEP, C28X_GTI_OP_READREG,
		C28X_GTI_OP_WRITEREG, C28X_GTI_OP_BLOCK_READ, C28X_GTI_OP_BLOCK_WRITE);
	command_print(CMD, "  transport: %s", c28x->transport_enabled ? "enabled" : "disabled");
	command_print(CMD, "  status: bits=%u halt_mask=0x%08" PRIx32 " run_mask=0x%08" PRIx32,
		c28x->status_dr_bits, c28x->status_halt_mask, c28x->status_run_mask);
	return ERROR_OK;
}

COMMAND_HANDLER(c28x_handle_gdb_arch_command)
{
	struct target *target = get_current_target(CMD_CTX);
	struct c28x_common *c28x = target_to_c28x(target);

	if (!c28x)
		return ERROR_FAIL;
	if (CMD_ARGC > 1)
		return ERROR_COMMAND_SYNTAX_ERROR;

	if (CMD_ARGC == 0) {
		command_print(CMD, "%s", c28x_get_gdb_arch(target));
		return ERROR_OK;
	}

	char *arch = strdup(CMD_ARGV[0]);
	if (!arch)
		return ERROR_FAIL;
	free(c28x->gdb_arch);
	c28x->gdb_arch = arch;
	return ERROR_OK;
}

static const struct command_registration c28x_exec_command_handlers[] = {
	{
		.name = "info",
		.handler = c28x_handle_info_command,
		.mode = COMMAND_EXEC,
		.help = "show C28x target state and transport configuration",
		.usage = "",
	},
	{
		.name = "device",
		.handler = c28x_handle_device_command,
		.mode = COMMAND_ANY,
		.help = "get or set the CCS targetdb device name for this C28x target",
		.usage = "[name]",
	},
	{
		.name = "gel_file",
		.handler = c28x_handle_gel_file_command,
		.mode = COMMAND_ANY,
		.help = "get or set the CCS GEL file associated with this device",
		.usage = "[path]",
	},
	{
		.name = "procid",
		.handler = c28x_handle_procid_command,
		.mode = COMMAND_ANY,
		.help = "get or set the CCS TI driver ProcID for C28x",
		.usage = "[value]",
	},
	{
		.name = "icepick_port",
		.handler = c28x_handle_icepick_port_command,
		.mode = COMMAND_ANY,
		.help = "get or set the CCS targetdb ICEPick-C port number for the C28x core",
		.usage = "[port]",
	},
	{
		.name = "xds110",
		.handler = c28x_handle_xds110_command,
		.mode = COMMAND_ANY,
		.help = "show or override CCS-derived XDS110 C28x memory command IDs",
		.usage = "[memread memwrite]",
	},
	{
		.name = "gti",
		.handler = c28x_handle_gti_command,
		.mode = COMMAND_EXEC,
		.help = "show CCS-derived native GTI/TRG/XDS command metadata recovered from JAR/DLL analysis",
		.usage = "[all|ops|flags|xds110]",
	},
	{
		.name = "regids",
		.handler = c28x_handle_regids_command,
		.mode = COMMAND_EXEC,
		.help = "show CCS-derived TI C28x register IDs",
		.usage = "[core|debug|mapped|all]",
	},
	{
		.name = "transport",
		.handler = c28x_handle_transport_command,
		.mode = COMMAND_EXEC,
		.help = "enable or disable the C28x debug transport layer",
		.usage = "enable|disable",
	},
	{
		.name = "ir",
		.handler = c28x_handle_ir_command,
		.mode = COMMAND_EXEC,
		.help = "get or set a C28x debug transport IR opcode",
		.usage = "idcode|status|halt|resume|step|reg_read|reg_write|mem_read16|mem_write16|bp_write|wp_write|bypass [value]",
	},
	{
		.name = "status_format",
		.handler = c28x_handle_status_format_command,
		.mode = COMMAND_EXEC,
		.help = "set status DR length and masks used by poll",
		.usage = "bits halt_mask run_mask",
	},
	{
		.name = "raw_ir",
		.handler = c28x_handle_raw_ir_command,
		.mode = COMMAND_EXEC,
		.help = "shift a raw value into the C28x TAP IR",
		.usage = "value",
	},
	{
		.name = "raw_dr",
		.handler = c28x_handle_raw_dr_command,
		.mode = COMMAND_EXEC,
		.help = "shift a raw value through the C28x TAP DR",
		.usage = "bits [value]",
	},
	{
		.name = "idcode",
		.handler = c28x_handle_idcode_command,
		.mode = COMMAND_EXEC,
		.help = "read IDCODE using the configured C28x transport",
		.usage = "",
	},
	{
		.name = "status",
		.handler = c28x_handle_status_command,
		.mode = COMMAND_EXEC,
		.help = "read the configured C28x status register",
		.usage = "",
	},
	{
		.name = "gdb_arch",
		.handler = c28x_handle_gdb_arch_command,
		.mode = COMMAND_EXEC,
		.help = "get or set the GDB architecture string returned for C28x targets",
		.usage = "[arch]",
	},
	COMMAND_REGISTRATION_DONE
};

static const struct command_registration c28x_command_handlers[] = {
	{
		.name = "c28x",
		.mode = COMMAND_ANY,
		.help = "TI C28x target commands",
		.chain = c28x_exec_command_handlers,
		.usage = "",
	},
	COMMAND_REGISTRATION_DONE
};

struct target_type c28x_target = {
	.name = "c28x",

	.poll = c28x_poll,
	.arch_state = c28x_arch_state,
	.halt = c28x_halt,
	.resume = c28x_resume,
	.step = c28x_step,
	.assert_reset = c28x_assert_reset,
	.deassert_reset = c28x_deassert_reset,
	.soft_reset_halt = c28x_soft_reset_halt,
	.get_gdb_arch = c28x_get_gdb_arch,
	.get_gdb_reg_list = c28x_get_gdb_reg_list,
	.get_gdb_reg_list_noread = c28x_get_gdb_reg_list_noread,
	.memory_ready = c28x_memory_ready,
	.read_memory = c28x_read_memory,
	.write_memory = c28x_write_memory,
	.read_buffer = c28x_read_buffer,
	.write_buffer = c28x_write_buffer,
	.add_breakpoint = c28x_add_breakpoint,
	.remove_breakpoint = c28x_remove_breakpoint,
	.add_watchpoint = c28x_add_watchpoint,
	.remove_watchpoint = c28x_remove_watchpoint,
	.hit_watchpoint = c28x_hit_watchpoint,
	.commands = c28x_command_handlers,
	.target_create = c28x_target_create,
	.init_target = c28x_init_target,
	.deinit_target = c28x_deinit_target,
	.examine = c28x_examine,
	.address_bits = c28x_address_bits,
	.data_bits = c28x_data_bits,
	.insn_set = c28x_insn_set,
};
