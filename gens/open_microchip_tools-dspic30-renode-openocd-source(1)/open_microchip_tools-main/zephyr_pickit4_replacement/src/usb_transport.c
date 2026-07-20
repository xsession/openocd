#include "usb_transport.h"

#include <errno.h>
#include <string.h>

#if defined(CONFIG_USB_DEVICE_STACK) && CONFIG_USB_DEVICE_STACK
#include <zephyr/logging/log.h>
#include <zephyr/sys/util.h>
#include <zephyr/usb/usb_ch9.h>
#include <zephyr/usb/usb_device.h>
#endif

#include "ri4_protocol.h"

#if defined(CONFIG_USB_DEVICE_STACK) && CONFIG_USB_DEVICE_STACK
LOG_MODULE_REGISTER(usb_transport, LOG_LEVEL_INF);

static struct device_state *g_state;
static uint8_t g_side_out[RI4_PACKET_SIZE];
static uint8_t g_data_out[RI4_PACKET_SIZE];
static size_t g_data_out_length;

static int handle_side_out(size_t length)
{
    struct ri4_response response;
    int rc;

    rc = ri4_handle_side_packet(g_state, g_side_out, length, g_data_out, g_data_out_length, &response);
    if (rc != 0) {
        LOG_ERR("RI4 side packet handling failed: %d", rc);
        return rc;
    }
    if (response.side_length > 0U) {
        (void)usb_write(RI4_SIDE_EP_IN, response.side_data, response.side_length, NULL);
    }
    if (response.data_length > 0U) {
        (void)usb_write(RI4_DATA_EP_IN, response.data_payload, response.data_length, NULL);
    }
    return 0;
}

static void side_out_cb(uint8_t ep, enum usb_dc_ep_cb_status_code status)
{
    uint32_t read = 0U;

    ARG_UNUSED(status);
    if (usb_read(ep, g_side_out, sizeof(g_side_out), &read) != 0) {
        LOG_ERR("usb_read failed on RI4 side OUT endpoint");
        return;
    }
    if (read > 0U) {
        (void)handle_side_out((size_t)read);
    }
}

static void data_out_cb(uint8_t ep, enum usb_dc_ep_cb_status_code status)
{
    uint32_t read = 0U;

    ARG_UNUSED(status);
    if (usb_read(ep, g_data_out, sizeof(g_data_out), &read) != 0) {
        LOG_ERR("usb_read failed on RI4 data OUT endpoint");
        return;
    }
    g_data_out_length = (size_t)read;
}

static struct usb_ep_cfg_data ep_cfg[] = {
    {
        .ep_cb = side_out_cb,
        .ep_addr = RI4_SIDE_EP_OUT,
    },
    {
        .ep_cb = data_out_cb,
        .ep_addr = RI4_DATA_EP_OUT,
    },
};

USBD_CLASS_DESCR_DEFINE(primary, 0) struct usb_if_descriptor ri4_if_desc = {
    .bLength = sizeof(struct usb_if_descriptor),
    .bDescriptorType = USB_DESC_INTERFACE,
    .bInterfaceNumber = 0,
    .bAlternateSetting = 0,
    .bNumEndpoints = 4,
    .bInterfaceClass = USB_BCC_VENDOR,
    .bInterfaceSubClass = 0,
    .bInterfaceProtocol = 0,
    .iInterface = 0,
};

USBD_CLASS_DESCR_DEFINE(primary, 1) struct usb_ep_descriptor ri4_side_out_desc = {
    .bLength = sizeof(struct usb_ep_descriptor),
    .bDescriptorType = USB_DESC_ENDPOINT,
    .bEndpointAddress = RI4_SIDE_EP_OUT,
    .bmAttributes = USB_DC_EP_BULK,
    .wMaxPacketSize = sys_cpu_to_le16(RI4_PACKET_SIZE),
    .bInterval = 0,
};

USBD_CLASS_DESCR_DEFINE(primary, 2) struct usb_ep_descriptor ri4_side_in_desc = {
    .bLength = sizeof(struct usb_ep_descriptor),
    .bDescriptorType = USB_DESC_ENDPOINT,
    .bEndpointAddress = RI4_SIDE_EP_IN,
    .bmAttributes = USB_DC_EP_BULK,
    .wMaxPacketSize = sys_cpu_to_le16(RI4_PACKET_SIZE),
    .bInterval = 0,
};

USBD_CLASS_DESCR_DEFINE(primary, 3) struct usb_ep_descriptor ri4_data_out_desc = {
    .bLength = sizeof(struct usb_ep_descriptor),
    .bDescriptorType = USB_DESC_ENDPOINT,
    .bEndpointAddress = RI4_DATA_EP_OUT,
    .bmAttributes = USB_DC_EP_BULK,
    .wMaxPacketSize = sys_cpu_to_le16(RI4_PACKET_SIZE),
    .bInterval = 0,
};

USBD_CLASS_DESCR_DEFINE(primary, 4) struct usb_ep_descriptor ri4_data_in_desc = {
    .bLength = sizeof(struct usb_ep_descriptor),
    .bDescriptorType = USB_DESC_ENDPOINT,
    .bEndpointAddress = RI4_DATA_EP_IN,
    .bmAttributes = USB_DC_EP_BULK,
    .wMaxPacketSize = sys_cpu_to_le16(RI4_PACKET_SIZE),
    .bInterval = 0,
};

static void status_cb(enum usb_dc_status_code status, const uint8_t *param)
{
    ARG_UNUSED(param);
    LOG_INF("USB status: %d", status);
}

static struct usb_cfg_data usb_config = {
    .usb_device_description = NULL,
    .interface = {
        .class_handler = NULL,
        .custom_handler = NULL,
        .vendor_handler = NULL,
    },
    .num_endpoints = ARRAY_SIZE(ep_cfg),
    .endpoint = ep_cfg,
    .cb_usb_status = status_cb,
};

int ri4_usb_transport_init(struct device_state *state)
{
    int rc;

    g_state = state;
    g_data_out_length = 0U;
    memset(g_side_out, 0, sizeof(g_side_out));
    memset(g_data_out, 0, sizeof(g_data_out));

    rc = usb_enable(&usb_config);
    if (rc != 0) {
        LOG_ERR("usb_enable failed: %d", rc);
        return rc;
    }

    LOG_INF("RI4 USB transport initialized");
    return 0;
}
#else
int ri4_usb_transport_init(struct device_state *state)
{
    ARG_UNUSED(state);
    return -ENOTSUP;
}
#endif