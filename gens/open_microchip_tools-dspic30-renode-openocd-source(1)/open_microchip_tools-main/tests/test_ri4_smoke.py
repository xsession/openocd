import struct
import unittest

from mchp_ri4.icd4_comms_usb import ICD4CommsUsb
from mchp_ri4.script import Script
from mchp_ri4.commands import Commands
from mchp_ri4.ri4_com import Ri4Com
from mchp_ri4.transport import FakeTransport
from mchp_ri4.errors import Ri4ProtocolError, Ri4TransportError


def _u32le(b: bytes, off: int) -> int:
    return struct.unpack_from("<I", b, off)[0]


class TestRi4SideChannelSmoke(unittest.TestCase):
    def test_script_add_params_header_and_utf16(self):
        s = Script(method="m", data=b"\xAA\xBB")
        out = s.add_params(0x11223344, "Hi")
        # paramSize = 4 (int) + 4 (utf16 'H''i')
        self.assertEqual(out[:4], struct.pack("<I", 8))
        self.assertEqual(out[4:8], struct.pack("<I", 2))
        self.assertEqual(out[8:12], struct.pack("<I", 0x11223344))
        self.assertEqual(out[12:16], "Hi".encode("utf-16le"))
        self.assertEqual(out[16:], b"\xAA\xBB")


    def test_fake_transport_preserves_unconsumed_bytes(self):
        transport = FakeTransport()
        transport.queue_recv(0x83, b"\x10\x11\x12\x13")

        self.assertEqual(transport.recv(0x83, 2, 100), b"\x10\x11")
        self.assertEqual(transport.recv(0x83, 2, 100), b"\x12\x13")

    def test_commands_run_script_with_upload(self):
        side_out = 0x02
        side_in = 0x81
        data_in = 0x83

        transport = None

        def queue_ack_ok():
            ack = b"".join(
                [
                    struct.pack("<I", ICD4CommsUsb.RESULT_RESPONSE_TYPE),
                    struct.pack("<I", 0),
                    struct.pack("<I", 20),
                    struct.pack("<I", 0),
                    struct.pack("<I", 0),
                ]
            )
            transport.queue_recv(side_in, ack)

        def queue_result_ok():
            resp = b"".join(
                [
                    struct.pack("<I", ICD4CommsUsb.RESULT_RESPONSE_TYPE),
                    struct.pack("<I", 0),
                    struct.pack("<I", 16),
                    struct.pack("<I", 0),
                ]
            )
            transport.queue_recv(side_in, resp)

        phase = {"n": 0}

        def on_send(ep: int, data: bytes, timeout_ms: int):
            if ep != side_out or len(data) < 16:
                return
            msg_type = _u32le(data, 0)
            if msg_type == (ICD4CommsUsb.SCRIPT_WITH_UPLOAD & 0xFFFFFFFF):
                queue_ack_ok()
                transport.queue_recv(data_in, b"\xDE\xAD\xBE\xEF")
                phase["n"] = 1
            elif msg_type == (ICD4CommsUsb.SCRDONE & 0xFFFFFFFF) and phase["n"] == 1:
                queue_result_ok()

        transport = FakeTransport(on_send=on_send)
        comm = ICD4CommsUsb(Ri4Com(transport))
        cmds = Commands(comm)
        data = cmds.run_script_with_upload(b"\x01\x02", 4, 7)
        self.assertEqual(data, b"\xDE\xAD\xBE\xEF")
    def test_get_status_value_from_key(self):
        side_out = 0x02
        side_in = 0x81

        transport = None

        def on_send(ep: int, data: bytes, timeout_ms: int):
            if ep != side_out:
                return
            if len(data) < 16:
                return
            msg_type = _u32le(data, 0)
            seq = _u32le(data, 4)
            if msg_type != ICD4CommsUsb.COMMAND_GET_STATUS_FROM_KEY:
                return

            val = b"7\x00"
            resp = b"".join(
                [
                    struct.pack("<I", msg_type),
                    struct.pack("<I", seq),
                    struct.pack("<I", 16 + len(val)),
                    struct.pack("<I", 0),
                    val,
                ]
            )
            transport.queue_recv(side_in, resp)

        transport = FakeTransport(on_send=on_send)
        com = Ri4Com(transport)
        icd = ICD4CommsUsb(com)

        res = icd.get_status_value_from_key("Commands in progress")
        self.assertEqual(res, "7")

    def test_exec_command_reads_fixed_length_response(self):
        side_out = 0x02
        side_in = 0x81

        transport = None

        def on_send(ep: int, data: bytes, timeout_ms: int):
            if ep != side_out:
                return
            if data != b"\xE1":
                return
            transport.queue_recv(side_in, b"\xAA\xBB\xCC\xDD\xEE")

        transport = FakeTransport(on_send=on_send)
        icd = ICD4CommsUsb(Ri4Com(transport))
        self.assertEqual(icd.exec_command(b"\xE1", 4), b"\xAA\xBB\xCC\xDD")

    def test_handle_ack_ok(self):
        transport = FakeTransport()
        icd = ICD4CommsUsb(Ri4Com(transport))
        ack = b"".join(
            [
                struct.pack("<I", 0),
                struct.pack("<I", 0),
                struct.pack("<I", 16),
                struct.pack("<I", 0),
            ]
        )
        icd.handle_ack(ack)

    def test_handle_ack_nonzero_status(self):
        transport = FakeTransport()
        icd = ICD4CommsUsb(Ri4Com(transport))
        ack = b"".join(
            [
                struct.pack("<I", 0),
                struct.pack("<I", 0),
                struct.pack("<I", 20),
                struct.pack("<I", 0),
                struct.pack("<I", 1),
            ]
        )
        with self.assertRaises(Ri4ProtocolError):
            icd.handle_ack(ack)

    def test_transfer_no_data(self):
        side_out = 0x02
        side_in = 0x81

        transport = None

        def on_send(ep: int, data: bytes, timeout_ms: int):
            if ep != side_out or len(data) < 16:
                return
            msg_type = _u32le(data, 0)
            if msg_type != (ICD4CommsUsb.SCRIPT_NO_DATA & 0xFFFFFFFF):
                return

            # Result response (type=13, bcount=16 => status=0, no payload)
            resp = b"".join(
                [
                    struct.pack("<I", ICD4CommsUsb.RESULT_RESPONSE_TYPE),
                    struct.pack("<I", 0),
                    struct.pack("<I", 16),
                    struct.pack("<I", 0),
                ]
            )
            transport.queue_recv(side_in, resp)

        transport = FakeTransport(on_send=on_send)
        icd = ICD4CommsUsb(Ri4Com(transport))
        cr = icd.transfer(b"\x01\x02", timeout_ms=1000)
        self.assertEqual(cr.status, 0)
        self.assertIsNone(cr.payload)

    def test_write_transfer_uses_operation_timeout_for_script_done(self):
        side_out = 0x02
        side_in = 0x81
        data_out = 0x04
        timeouts = []
        state = {"phase": 0}

        transport = None

        def queue_ack_ok():
            ack = b"".join(
                [
                    struct.pack("<I", ICD4CommsUsb.RESULT_RESPONSE_TYPE),
                    struct.pack("<I", 0),
                    struct.pack("<I", 20),
                    struct.pack("<I", 0),
                    struct.pack("<I", 0),
                ]
            )
            transport.queue_recv(side_in, ack)

        def queue_result_ok():
            resp = b"".join(
                [
                    struct.pack("<I", ICD4CommsUsb.RESULT_RESPONSE_TYPE),
                    struct.pack("<I", 0),
                    struct.pack("<I", 16),
                    struct.pack("<I", 0),
                ]
            )
            transport.queue_recv(side_in, resp)

        def on_send(ep: int, data: bytes, timeout_ms: int):
            if ep == side_out and len(data) >= 16:
                msg_type = _u32le(data, 0)
                if msg_type == (ICD4CommsUsb.SCRIPT_WITH_DOWNLOAD & 0xFFFFFFFF):
                    timeouts.append(timeout_ms)
                    queue_ack_ok()
                    state["phase"] = 1
                elif msg_type == (ICD4CommsUsb.SCRDONE & 0xFFFFFFFF) and state["phase"] == 2:
                    timeouts.append(timeout_ms)
                    queue_result_ok()
            elif ep == data_out:
                state["phase"] = 2

        transport = FakeTransport(on_send=on_send)
        icd = ICD4CommsUsb(Ri4Com(transport))

        cr = icd.write_transfer(b"\xAA", b"\x10\x11", timeout_ms=1234)

        self.assertEqual(cr.status, 0)
        self.assertEqual(timeouts, [1234, 1234])

    def test_read_transfer_upload(self):
        side_out = 0x02
        side_in = 0x81
        data_in = 0x83

        transport = None

        def queue_ack_ok():
            ack = b"".join(
                [
                    struct.pack("<I", ICD4CommsUsb.RESULT_RESPONSE_TYPE),
                    struct.pack("<I", 0),
                    struct.pack("<I", 20),
                    struct.pack("<I", 0),
                    struct.pack("<I", 0),
                ]
            )
            transport.queue_recv(side_in, ack)

        def queue_result_ok():
            resp = b"".join(
                [
                    struct.pack("<I", ICD4CommsUsb.RESULT_RESPONSE_TYPE),
                    struct.pack("<I", 0),
                    struct.pack("<I", 16),
                    struct.pack("<I", 0),
                ]
            )
            transport.queue_recv(side_in, resp)

        state = {"phase": 0}

        def on_send(ep: int, data: bytes, timeout_ms: int):
            if ep != side_out or len(data) < 16:
                return
            msg_type = _u32le(data, 0)
            if msg_type == (ICD4CommsUsb.SCRIPT_WITH_UPLOAD & 0xFFFFFFFF):
                queue_ack_ok()
                # Data channel bytes for the upload.
                transport.queue_recv(data_in, b"\x10\x11\x12\x13")
                state["phase"] = 1
            elif msg_type == (ICD4CommsUsb.SCRDONE & 0xFFFFFFFF) and state["phase"] == 1:
                queue_result_ok()

        transport = FakeTransport(on_send=on_send)
        icd = ICD4CommsUsb(Ri4Com(transport))
        cr, data = icd.read_transfer(b"\xaa", 4, timeout_ms=1000)
        self.assertEqual(cr.status, 0)
        self.assertEqual(data, b"\x10\x11\x12\x13")

    def test_read_transfer_upload_accumulates_fragmented_data_reads(self):
        side_out = 0x02
        side_in = 0x81
        data_in = 0x83

        def queue_ack_ok():
            ack = b"".join(
                [
                    struct.pack("<I", ICD4CommsUsb.RESULT_RESPONSE_TYPE),
                    struct.pack("<I", 0),
                    struct.pack("<I", 20),
                    struct.pack("<I", 0),
                    struct.pack("<I", 0),
                ]
            )
            transport.queue_recv(side_in, ack)

        def queue_result_ok():
            resp = b"".join(
                [
                    struct.pack("<I", ICD4CommsUsb.RESULT_RESPONSE_TYPE),
                    struct.pack("<I", 0),
                    struct.pack("<I", 16),
                    struct.pack("<I", 0),
                ]
            )
            transport.queue_recv(side_in, resp)

        class FragmentingTransport(FakeTransport):
            def recv(self, endpoint: int, length: int, timeout_ms: int) -> bytes:
                q = self._queues.get(endpoint)
                if not q:
                    raise Ri4TransportError(f"No queued response for endpoint 0x{endpoint:02x}")
                data = q.popleft()
                if endpoint == data_in and len(data) > 2:
                    head = data[:2]
                    tail = data[2:]
                    q.appendleft(tail)
                    return head
                if len(data) > length:
                    head = data[:length]
                    tail = data[length:]
                    q.appendleft(tail)
                    return head
                return data

        transport = None
        state = {"phase": 0}

        def on_send(ep: int, data: bytes, timeout_ms: int):
            if ep != side_out or len(data) < 16:
                return
            msg_type = _u32le(data, 0)
            if msg_type == (ICD4CommsUsb.SCRIPT_WITH_UPLOAD & 0xFFFFFFFF):
                queue_ack_ok()
                transport.queue_recv(data_in, b"\x10\x11\x12\x13")
                state["phase"] = 1
            elif msg_type == (ICD4CommsUsb.SCRDONE & 0xFFFFFFFF) and state["phase"] == 1:
                queue_result_ok()

        transport = FragmentingTransport(on_send=on_send)
        icd = ICD4CommsUsb(Ri4Com(transport))

        cr, data = icd.read_transfer(b"\xaa", 4, timeout_ms=1000)

        self.assertEqual(cr.status, 0)
        self.assertEqual(data, b"\x10\x11\x12\x13")

    def test_write_transfer_download(self):
        side_out = 0x02
        side_in = 0x81
        data_out = 0x04

        seen = {"data": b""}
        transport = None

        def queue_ack_ok():
            ack = b"".join(
                [
                    struct.pack("<I", ICD4CommsUsb.RESULT_RESPONSE_TYPE),
                    struct.pack("<I", 0),
                    struct.pack("<I", 20),
                    struct.pack("<I", 0),
                    struct.pack("<I", 0),
                ]
            )
            transport.queue_recv(side_in, ack)

        def queue_result_ok():
            resp = b"".join(
                [
                    struct.pack("<I", ICD4CommsUsb.RESULT_RESPONSE_TYPE),
                    struct.pack("<I", 0),
                    struct.pack("<I", 16),
                    struct.pack("<I", 0),
                ]
            )
            transport.queue_recv(side_in, resp)

        state = {"phase": 0}

        def on_send(ep: int, data: bytes, timeout_ms: int):
            if ep == data_out:
                seen["data"] += data
                return
            if ep != side_out or len(data) < 16:
                return
            msg_type = _u32le(data, 0)
            if msg_type == (ICD4CommsUsb.SCRIPT_WITH_DOWNLOAD & 0xFFFFFFFF):
                queue_ack_ok()
                state["phase"] = 1
            elif msg_type == (ICD4CommsUsb.SCRDONE & 0xFFFFFFFF) and state["phase"] == 1:
                queue_result_ok()

        transport = FakeTransport(on_send=on_send)
        icd = ICD4CommsUsb(Ri4Com(transport))
        cr = icd.write_transfer(b"\xbb", b"\x01\x02\x03\x04", timeout_ms=1000)
        self.assertEqual(cr.status, 0)
        self.assertEqual(seen["data"], b"\x01\x02\x03\x04")

    def test_read_transfer_uses_bounded_data_timeout(self):
        side_out = 0x02
        side_in = 0x81
        data_in = 0x83

        class RecordingTransport(FakeTransport):
            def __init__(self, *, on_send=None):
                super().__init__(on_send=on_send)
                self.recv_calls = []

            def recv(self, endpoint: int, length: int, timeout_ms: int) -> bytes:
                self.recv_calls.append((endpoint, length, timeout_ms))
                return super().recv(endpoint, length, timeout_ms)

        transport = None

        def on_send(ep: int, data: bytes, timeout_ms: int):
            if ep != side_out or len(data) < 16:
                return
            msg_type = _u32le(data, 0)
            if msg_type == (ICD4CommsUsb.SCRIPT_WITH_UPLOAD & 0xFFFFFFFF):
                ack = b"".join(
                    [
                        struct.pack("<I", ICD4CommsUsb.RESULT_RESPONSE_TYPE),
                        struct.pack("<I", 0),
                        struct.pack("<I", 20),
                        struct.pack("<I", 0),
                        struct.pack("<I", 0),
                    ]
                )
                transport.queue_recv(side_in, ack)

        transport = RecordingTransport(on_send=on_send)
        icd = ICD4CommsUsb(Ri4Com(transport))

        with self.assertRaises(Ri4TransportError):
            icd.read_transfer(b"\xaa", 4, timeout_ms=1000)

        data_recv = [call for call in transport.recv_calls if call[0] == data_in]
        self.assertEqual(len(data_recv), 1)
        self.assertEqual(data_recv[0][2], ICD4CommsUsb.DATA_ENDPOINT_TIMEOUT_MS)

    def test_transfer_attempts_abort_recovery_after_side_timeout(self):
        side_out = 0x02
        side_in = 0x81

        seen_types = []
        transport = None

        def on_send(ep: int, data: bytes, timeout_ms: int):
            if ep != side_out:
                return
            if len(data) == 1:
                return
            msg_type = _u32le(data, 0)
            seen_types.append(msg_type)
            if msg_type == ICD4CommsUsb.COMMAND_ABORT_SCRIPTING_ENGINE:
                transport.queue_recv(
                    side_in,
                    b"".join(
                        [
                            struct.pack("<I", ICD4CommsUsb.RESULT_RESPONSE_TYPE),
                            struct.pack("<I", 0),
                            struct.pack("<I", 16),
                            struct.pack("<I", 0),
                        ]
                    ),
                )

        transport = FakeTransport(on_send=on_send)
        icd = ICD4CommsUsb(Ri4Com(transport))

        with self.assertRaises(Ri4TransportError):
            icd.transfer(b"\x39\x01", timeout_ms=1000)

        self.assertEqual(seen_types[0], ICD4CommsUsb.SCRIPT_NO_DATA & 0xFFFFFFFF)
        self.assertIn(ICD4CommsUsb.COMMAND_ABORT_SCRIPTING_ENGINE, seen_types)


if __name__ == "__main__":
    unittest.main()
