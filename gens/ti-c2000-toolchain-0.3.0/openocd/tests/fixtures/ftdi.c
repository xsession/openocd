#include <stdbool.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

struct mpsse_ctx { int unused; };
static struct mpsse_ctx *mpsse_ctx;

struct signal {
	const char *name;
	uint16_t data_mask;
	uint16_t input_mask;
	uint16_t oe_mask;
	bool invert_data;
	bool invert_input;
	bool invert_oe;
	struct signal *next;
};

static struct signal *signals;

/* FIXME: Where to store per-instance data? We need an SWD context. */
static struct swd_cmd_queue_entry {
	uint8_t cmd;
} *swd_cmd_queue;

static uint16_t output;
static uint16_t direction;
static int freq;

#define COMMAND_HANDLER(name) int name(int CMD_ARGC, const char **CMD_ARGV)
#define ERROR_OK 0
#define ERROR_FAIL -1
#define ERROR_COMMAND_SYNTAX_ERROR -2
#define ERROR_JTAG_INIT_FAILED -3
#define COMMAND_CONFIG 1
#define COMMAND_EXEC 2
#define LOG_ERROR(...) do { } while (0)

static struct signal *find_signal_by_name(const char *name) { (void)name; return signals; }
static int ftdi_set_signal(const struct signal *signal, char value) { (void)signal; (void)value; return 0; }
static void mpsse_set_data_bits_low_byte(struct mpsse_ctx *ctx, int value, int dir) { (void)ctx; (void)value; (void)dir; }
static void mpsse_set_data_bits_high_byte(struct mpsse_ctx *ctx, int value, int dir) { (void)ctx; (void)value; (void)dir; }
static void mpsse_loopback_config(struct mpsse_ctx *ctx, bool enable) { (void)ctx; (void)enable; }
static int mpsse_set_frequency(struct mpsse_ctx *ctx, int value) { (void)ctx; return value; }
static int adapter_get_speed_khz(void) { return 1000; }
static int mpsse_flush(struct mpsse_ctx *ctx) { (void)ctx; return ERROR_OK; }
static void mpsse_close(struct mpsse_ctx *ctx) { (void)ctx; }

static int ftdi_initialize(void)
{
	mpsse_set_data_bits_low_byte(mpsse_ctx, output & 0xff, direction & 0xff);
	mpsse_set_data_bits_high_byte(mpsse_ctx, output >> 8, direction >> 8);

	mpsse_loopback_config(mpsse_ctx, false);

	freq = mpsse_set_frequency(mpsse_ctx, adapter_get_speed_khz() * 1000);
	return mpsse_flush(mpsse_ctx);
}

COMMAND_HANDLER(ftdi_handle_set_signal_command)
{
	return ERROR_OK;
}

COMMAND_HANDLER(ftdi_handle_get_signal_command)
{
	return ERROR_OK;
}

struct command_registration {
	const char *name;
	void *handler;
	int mode;
	const char *help;
	const char *usage;
};

static const struct command_registration ftdi_subcommand_handlers[] = {
	{
		.name = "set_signal",
		.handler = &ftdi_handle_set_signal_command,
		.mode = COMMAND_EXEC,
		.help = "control a layout-specific signal",
		.usage = "name (1|0|z)",
	},
};

static int ftdi_quit(void)
{
	mpsse_close(mpsse_ctx);
	struct signal *sig = signals;
	while (sig) {
		struct signal *next = sig->next;
		free((void *)sig->name);
		free(sig);
		sig = next;
	}
	free(swd_cmd_queue);
	return ERROR_OK;
}
