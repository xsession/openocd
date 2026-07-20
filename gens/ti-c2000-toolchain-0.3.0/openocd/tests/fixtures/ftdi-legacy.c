#include <stdlib.h>
#include <string.h>

struct signal {
	const char *name;
	unsigned short data_mask;
	unsigned short input_mask;
	unsigned short oe_mask;
	int invert_data;
	int invert_input;
	int invert_oe;
	struct signal *next;
};

static struct signal *signals;
static void *mpsse_ctx;
static unsigned short output;
static unsigned short direction;
static char *ftdi_device_desc;

#define COMMAND_HANDLER(name) int name(int CMD_ARGC, const char **CMD_ARGV)
#define ERROR_OK 0
#define ERROR_FAIL -1
#define ERROR_COMMAND_SYNTAX_ERROR -2
#define ERROR_JTAG_INIT_FAILED -3
#define COMMAND_CONFIG 1
#define LOG_ERROR(...) do { } while (0)

static struct signal *find_signal_by_name(const char *name) { (void)name; return signals; }
static int ftdi_set_signal(const struct signal *signal, char value) { (void)signal; (void)value; return 0; }
static void mpsse_set_data_bits_low_byte(void *ctx, int value, int dir) { (void)ctx; (void)value; (void)dir; }
static void mpsse_set_data_bits_high_byte(void *ctx, int value, int dir) { (void)ctx; (void)value; (void)dir; }
static int mpsse_flush(void *ctx) { (void)ctx; return ERROR_OK; }

static int ftdi_initialize(void)
{
	mpsse_set_data_bits_low_byte(mpsse_ctx, output & 0xff, direction & 0xff);
	mpsse_set_data_bits_high_byte(mpsse_ctx, output >> 8, direction >> 8);
	return ERROR_OK;
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
		.mode = 2,
		.help = "control a layout-specific signal",
		.usage = "name (1|0|z)",
	},
};

static int ftdi_quit(void)
{
	free(ftdi_device_desc);
	return ERROR_OK;
}
