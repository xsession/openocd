import struct
import unittest

from mchp_ri4.commands import Commands
from mchp_ri4.icd4_comms_usb import ICD4CommsUsb
from mchp_ri4.power_control import (
    Ri4PowerController,
    build_init_power_script,
    parse_power_status_payload,
)
from mchp_ri4.errors import Ri4TransportError
from mchp_ri4.ri4_com import Ri4Com
from mchp_ri4.transport import FakeTransport


def _u32le(buf: bytes, off: int) -> int:
    return struct.unpack_from("<I", buf, off)[0]


def _extract_script(data: bytes) -> bytes:
    payload = data[16:_u32le(data, 8)]
    param_size = _u32le(payload, 0)
    script_size = _u32le(payload, 4)
    return payload[8 + param_size : 8 + param_size + script_size]


def _result(status: int = 0, payload: bytes = b"") -> bytes:
    if not payload:
        return b"".join(
            [
                struct.pack("<I", ICD4CommsUsb.RESULT_RESPONSE_TYPE),
                struct.pack("<I", 0),
                struct.pack("<I", 16),
                struct.pack("<I", 0),
            ]
        )
    return b"".join(
        [
            struct.pack("<I", ICD4CommsUsb.RESULT_RESPONSE_TYPE),
            struct.pack("<I", 0),
            struct.pack("<I", 24 + len(payload)),
            struct.pack("<I", 0),
            struct.pack("<I", status),
            struct.pack("<I", len(payload)),
            payload,
        ]
    )


class TestPowerControl(unittest.TestCase):
    def test_build_init_power_script_for_five_volts(self):
        script = build_init_power_script(5000, 5000, 5000)
        self.assertEqual(script, bytes((0x40, 0x88, 0x13, 0x00, 0x00, 0x88, 0x13, 0x00, 0x00, 0x88, 0x13, 0x00, 0x00, 0x42, 0x43)))

    def test_parse_power_status_payload(self):
        payload = b"".join(struct.pack("<I", value) for value in (5000, 4991, 0, 0, 4988, 31, 12, 4990))
        status = parse_power_status_payload(payload)
        self.assertEqual(status.target_vdd_mv, 4991)
        self.assertEqual(status.vdd_voltage_sense_mv, 4990)

    def test_power_target_sequence_and_status(self):
        side_out = 0x02
        side_in = 0x81
        seen = []
        timeouts = []

        transport = None

        status_payload = b"".join(struct.pack("<I", value) for value in (5000, 5000, 0, 0, 4998, 30, 11, 5001))

        def on_send(ep: int, data: bytes, timeout_ms: int):
            if ep != side_out or len(data) < 16:
                return
            msg_type = _u32le(data, 0)
            if msg_type != (ICD4CommsUsb.SCRIPT_NO_DATA & 0xFFFFFFFF):
                return
            script = _extract_script(data)
            seen.append(script)
            timeouts.append(timeout_ms)
            if script[:1] == b"\x47":
                transport.queue_recv(side_in, _result(payload=status_payload))
            else:
                transport.queue_recv(side_in, _result())

        transport = FakeTransport(on_send=on_send)
        controller = Ri4PowerController(Commands(ICD4CommsUsb(Ri4Com(transport))))

        result = controller.power_target(5000)

        self.assertEqual(seen[0], bytes((0x39, 0x01)))
        self.assertEqual(seen[1], bytes((0x46, 0x01, 0x00, 0x00, 0x00)))
        self.assertEqual(seen[2], bytes((0x44,)))
        self.assertEqual(seen[3], build_init_power_script(5000, 5000, 5000))
        self.assertEqual(seen[4], bytes((0x00, 0x01)))
        self.assertEqual(seen[5], bytes((0x47,)))
        self.assertTrue(all(timeout == Ri4PowerController.POWER_SCRIPT_TIMEOUT_MS for timeout in timeouts))
        self.assertEqual(result["status"]["targetVddMv"], 5000)

    def test_power_target_without_live_connect_skips_live_connect_script(self):
        side_out = 0x02
        side_in = 0x81
        seen = []

        transport = None

        status_payload = b"".join(struct.pack("<I", value) for value in (5000, 5000, 0, 0, 4998, 30, 11, 5001))

        def on_send(ep: int, data: bytes, timeout_ms: int):
            if ep != side_out or len(data) < 16:
                return
            msg_type = _u32le(data, 0)
            if msg_type != (ICD4CommsUsb.SCRIPT_NO_DATA & 0xFFFFFFFF):
                return
            script = _extract_script(data)
            seen.append(script)
            if script[:1] == b"\x47":
                transport.queue_recv(side_in, _result(payload=status_payload))
            else:
                transport.queue_recv(side_in, _result())

        transport = FakeTransport(on_send=on_send)
        controller = Ri4PowerController(Commands(ICD4CommsUsb(Ri4Com(transport))))

        result = controller.power_target(5000, live_connect=False)

        self.assertEqual(seen[0], bytes((0x46, 0x01, 0x00, 0x00, 0x00)))
        self.assertNotIn(bytes((0x39, 0x00)), seen)
        self.assertEqual(result["liveConnect"], False)

    def test_power_target_precleans_and_retries_once(self):
        controller = Ri4PowerController(Commands(ICD4CommsUsb(Ri4Com(FakeTransport()))))
        calls = []

        controller._preclean_scripting_engine = lambda: calls.append("preclean")  # type: ignore[method-assign]

        attempts = {"live": 0}

        def fake_live_connect(enable: bool):
            calls.append(("live", enable))
            attempts["live"] += 1
            if attempts["live"] == 1:
                raise Ri4TransportError("stale state")
            return {"liveConnect": enable, "status": 0}

        controller.set_live_connect = fake_live_connect  # type: ignore[method-assign]
        controller.select_power_source = lambda from_tool: calls.append(("source", from_tool)) or {"status": 0}  # type: ignore[method-assign]
        controller.shutdown_power = lambda: calls.append("shutdown") or {"status": 0}  # type: ignore[method-assign]
        controller.init_power = lambda voltage_mv, **kwargs: calls.append(("init", voltage_mv)) or {"status": 0}  # type: ignore[method-assign]
        controller.set_maintain_active_power = lambda enable: calls.append(("maintain", enable)) or {"status": 0}  # type: ignore[method-assign]
        controller.get_power_status = lambda: {"targetVddMv": 5000}  # type: ignore[method-assign]

        result = controller.power_target(5000)

        self.assertEqual(calls[:3], ["preclean", ("live", True), "preclean"])
        self.assertEqual(result["status"]["targetVddMv"], 5000)


if __name__ == "__main__":
    unittest.main()