from __future__ import annotations

import socketserver
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from mchp_openocd.bridge_server import BridgeConfig, BridgeProtocol, BridgeState
from mchp_renode_cosim.gdb_session import RenodeGdbSession, RenodeSessionError, profile_for_core
from mchp_simulator.firmware_image import FirmwareImage, Segment
from mchp_gdbrsp.rsp import encode_packet


class _FakeRenodeGdbHandler(socketserver.BaseRequestHandler):
    def handle(self) -> None:
        self.request.settimeout(0.2)
        memory = bytearray([0xFF]) * 0x110000
        registers = {1: bytearray(2), 3: bytearray(4), 16: bytearray(4)}
        no_ack = False
        running = False
        breakpoints = set()
        buf = bytearray()

        def send_packet(payload: bytes) -> None:
            self.request.sendall(encode_packet(payload))

        def reply(payload: bytes) -> None:
            send_packet(payload)

        while True:
            try:
                data = self.request.recv(4096)
            except TimeoutError:
                continue
            if not data:
                return
            buf.extend(data)

            while buf:
                if buf[0] in (ord("+"), ord("-")):
                    del buf[0]
                    continue
                if buf[0] == 0x03:
                    del buf[0]
                    if running:
                        running = False
                        reply(b"T02")
                    continue
                if buf[0] != ord("$"):
                    del buf[0]
                    continue
                try:
                    hash_index = buf.index(ord("#"))
                except ValueError:
                    break
                if len(buf) < hash_index + 3:
                    break
                payload = bytes(buf[1:hash_index])
                del buf[: hash_index + 3]
                if not no_ack:
                    self.request.sendall(b"+")

                text = payload.decode("ascii", errors="replace")
                if text == "qSupported":
                    reply(b"PacketSize=4000;QStartNoAckMode+;hwbreak+;swbreak+")
                elif text == "QStartNoAckMode":
                    reply(b"OK")
                    no_ack = True
                elif text == "?":
                    reply(b"T05")
                elif text.startswith("p"):
                    number = int(text[1:], 16)
                    value = registers.get(number)
                    reply(b"E01" if value is None else bytes(value).hex().encode("ascii"))
                elif text.startswith("P"):
                    number_text, value_text = text[1:].split("=", 1)
                    number = int(number_text, 16)
                    registers[number] = bytearray.fromhex(value_text)
                    reply(b"OK")
                elif text.startswith("m"):
                    address_text, length_text = text[1:].split(",", 1)
                    address = int(address_text, 16)
                    length = int(length_text, 16)
                    reply(memory[address : address + length].hex().encode("ascii"))
                elif text.startswith("M"):
                    range_text, data_text = text[1:].split(":", 1)
                    address_text, length_text = range_text.split(",", 1)
                    address = int(address_text, 16)
                    length = int(length_text, 16)
                    data_bytes = bytes.fromhex(data_text)
                    if len(data_bytes) != length:
                        reply(b"E02")
                    else:
                        memory[address : address + length] = data_bytes
                        reply(b"OK")
                elif text.startswith("Z") or text.startswith("z"):
                    insert = text[0] == "Z"
                    bp_type, address, kind = (int(part, 16) for part in text[1:].split(","))
                    key = (bp_type, address, kind)
                    if insert:
                        breakpoints.add(key)
                    else:
                        breakpoints.discard(key)
                    reply(b"OK")
                elif text == "c":
                    running = True
                    # Deliberately no reply until Ctrl-C, like a real GDB target.
                elif text == "s":
                    current = int.from_bytes(registers[3], "little")
                    registers[3] = bytearray((current + 2).to_bytes(4, "little"))
                    reply(b"T05")
                elif text.startswith("qRcmd,"):
                    command = bytes.fromhex(text.split(",", 1)[1]).decode("utf-8")
                    if command == "start":
                        reply(b"O" + b"emulation started\n".hex().encode("ascii"))
                        reply(b"OK")
                    elif command == "machine Reset":
                        for number, value in list(registers.items()):
                            registers[number] = bytearray(len(value))
                        reply(b"O" + b"machine reset\n".hex().encode("ascii"))
                        reply(b"OK")
                    else:
                        reply(b"E03")
                else:
                    reply(b"")


class _ThreadingTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


class TestRenodeCoreProfiles(unittest.TestCase):
    def test_custom_core_register_and_flash_profiles(self) -> None:
        pic16 = profile_for_core("PIC16F_TEST")
        pic18 = profile_for_core("PIC18F_TEST")
        dspic30 = profile_for_core("dsPIC30F5011")
        dspic33 = profile_for_core("dsPIC33EP_TEST")
        self.assertEqual((pic16.pc_register, pic16.pc_bytes, pic16.flash_size), (1, 2, 0x4000))
        self.assertEqual((pic18.pc_register, pic18.pc_bytes, pic18.flash_size), (3, 4, 0x20000))
        self.assertEqual(
            (
                dspic30.pc_register,
                dspic30.pc_bytes,
                dspic30.flash_base,
                dspic30.flash_size,
                dspic30.image_address_bias,
            ),
            (16, 4, 0x100000, 0xAC00, 0x100000),
        )
        self.assertEqual((dspic33.pc_register, dspic33.pc_bytes, dspic33.flash_size), (16, 4, 0x40000))


class TestRenodeGdbSession(unittest.TestCase):
    def setUp(self) -> None:
        self.server = _ThreadingTCPServer(("127.0.0.1", 0), _FakeRenodeGdbHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        host, port = self.server.server_address
        self.session = RenodeGdbSession.open_gdb(
            host=host,
            port=port,
            processor="PIC18F_TEST",
            family="PIC18",
            timeout=1.0,
            flash_size=64,
            transfer_chunk_size=16,
        )

    def tearDown(self) -> None:
        self.session.close()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2.0)

    def test_debug_control_pc_breakpoints_and_watchpoints(self) -> None:
        inventory = self.session.script_inventory()
        self.assertEqual(inventory["backend"], "renode-gdb")
        self.assertEqual(inventory["pcRegister"], 3)
        self.assertTrue(inventory["capabilities"]["watchpoints"])

        self.session.set_pc(0x120)
        self.assertEqual(self.session.get_pc()["pc"], 0x120)
        stepped = self.session.step_target()
        self.assertEqual(stepped["pc"], 0x122)
        self.assertEqual(stepped["signal"], 5)

        bp = self.session.add_breakpoint(0x200, kind=2)
        wp = self.session.add_watchpoint(0x80, length=4, access="write")
        self.assertEqual((bp["slot"], wp["slot"]), (0, 1))
        self.assertTrue(self.session.remove_breakpoint(0x200)["removed"])
        self.assertTrue(self.session.remove_watchpoint(0x80)["removed"])

        self.assertEqual(self.session.run_target()["state"], "running")
        for _ in range(20):
            if self.session.target_status()["running"]:
                break
            time.sleep(0.01)
        halted = self.session.halt_target()
        self.assertEqual(halted["state"], "halted")
        self.assertEqual(halted["signal"], 2)

        reset = self.session.reset_target()
        self.assertEqual(reset["pc"], 0)
        self.assertIn("machine reset", reset["output"])

    def test_erase_program_verify_and_memory_access(self) -> None:
        self.session.write_program(0, b"\x00" * 64)
        erased = self.session.erase()
        self.assertEqual(erased["chunks"], 4)
        self.assertEqual(bytes.fromhex(self.session.read_program(0, 64)["dataHex"]), b"\xFF" * 64)

        image = FirmwareImage(segments=(Segment(4, b"\x01\x02\x03\x04"), Segment(16, b"hello")))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "firmware.hex"
            image.to_intel_hex_path(str(path))
            result = self.session.program_hex(str(path), erase_first=True, verify=True, chunk_size=3)
            self.assertEqual(result["bytesProgrammed"], 9)
            self.assertTrue(result["verify"]["verified"])

            self.session.write_program(5, b"\x99")
            with self.assertRaisesRegex(RenodeSessionError, "Verification failed at 0x5"):
                self.session.verify_hex(str(path))

    def test_ri4_scripts_are_explicitly_unavailable(self) -> None:
        with self.assertRaisesRegex(RenodeSessionError, "unavailable"):
            self.session.run_script("EnterDebugMode")

    def test_dspic30_logical_image_is_relocated_to_harvard_flash_window(self) -> None:
        host, port = self.server.server_address
        session = RenodeGdbSession.open_gdb(
            host=host,
            port=port,
            processor="dsPIC30F5011",
            family="DSPIC30F",
            timeout=1.0,
            transfer_chunk_size=16,
        )
        try:
            image = FirmwareImage(segments=(Segment(4, b"\x12\x34\x56\x78"),))
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "dspic30.hex"
                image.to_intel_hex_path(str(path))
                result = session.program_hex(str(path), erase_first=True, verify=True)
                self.assertEqual(result["segments"][0]["address"], 4)
                self.assertEqual(result["segments"][0]["targetAddress"], 0x100004)
                self.assertEqual(
                    bytes.fromhex(session.read_program(0x100004, 4)["dataHex"]),
                    b"\x12\x34\x56\x78",
                )
                self.assertTrue(result["verify"]["verified"])
        finally:
            session.close()


class TestRenodeBridgeDispatch(unittest.TestCase):
    def test_start_session_uses_renode_backend_without_device_pack(self) -> None:
        state = BridgeState(BridgeConfig(backend="renode", renode_port=4444))
        protocol = BridgeProtocol(state)
        with patch("mchp_openocd.bridge_server.RenodeGdbSession") as session_type:
            session = session_type.open_gdb.return_value
            session.script_inventory.return_value = {"backend": "renode-gdb"}
            response = protocol.handle(
                {
                    "command": "startSession",
                    "args": {"processor": "PIC18F_TEST", "family": "PIC18", "pcBytes": 4},
                }
            )

        self.assertTrue(response["ok"])
        self.assertEqual(response["result"]["backend"], "renode-gdb")
        kwargs = session_type.open_gdb.call_args.kwargs
        self.assertEqual(kwargs["port"], 4444)
        self.assertEqual(kwargs["processor"], "PIC18F_TEST")
        self.assertNotIn("scripts_path", kwargs)


if __name__ == "__main__":
    unittest.main()
