import struct
import tempfile
import textwrap
import unittest
from pathlib import Path

from mchp_ri4 import Commands, DeviceFile, ICD4CommsUsb, NamedScriptSession, Ri4Com
from mchp_ri4.family_profiles import get_family_profile
from mchp_ri4.transport import FakeTransport
from mchp_simulator.firmware_image import FirmwareImage, Segment


def _u32le(buf: bytes, off: int = 0) -> int:
    return struct.unpack_from("<I", buf, off)[0]


def _ack_ok() -> bytes:
    return b"".join(
        [
            struct.pack("<I", ICD4CommsUsb.RESULT_RESPONSE_TYPE),
            struct.pack("<I", 0),
            struct.pack("<I", 20),
            struct.pack("<I", 0),
            struct.pack("<I", 0),
        ]
    )


def _result_ok() -> bytes:
    return b"".join(
        [
            struct.pack("<I", ICD4CommsUsb.RESULT_RESPONSE_TYPE),
            struct.pack("<I", 0),
            struct.pack("<I", 16),
            struct.pack("<I", 0),
        ]
    )


class TestNamedScriptSession(unittest.TestCase):
    def test_enter_programming_mode_primes_icsp_speed(self):
        xml = textwrap.dedent(
            """
            <devicefile>
              <processor>dsPIC30F5011</processor>
              <script><function>SetSpeedFromDevice</function><scrbytes><byte>0xEC</byte></scrbytes></script>
              <script><function>EnterTMOD_HV</function><scrbytes><byte>0xB6</byte></scrbytes></script>
            </devicefile>
            """
        )
        session = NamedScriptSession(
            commands=Commands(ICD4CommsUsb(Ri4Com(FakeTransport()))),
            device_file=DeviceFile.from_xml_text("dsPIC30F5011", xml),
            processor="dsPIC30F5011",
            family="DSPIC30F",
        )

        seen = []
        session.run_script = lambda name, *params, timeout_ms=-1: seen.append(name) or {  # type: ignore[method-assign]
            "script": name,
            "status": 0,
            "payloadHex": "",
        }

        result = session.enter_programming_mode()

        self.assertEqual(seen, ["SetSpeedFromDevice", "EnterTMOD_HV"])
        self.assertEqual(result["script"], "EnterTMOD_HV")

    def test_enter_programming_mode_retries_icsp_speed_once(self):
        xml = textwrap.dedent(
            """
            <devicefile>
              <processor>dsPIC30F5011</processor>
              <script><function>SetSpeedFromDevice</function><scrbytes><byte>0xEC</byte></scrbytes></script>
              <script><function>EnterTMOD_HV</function><scrbytes><byte>0xB6</byte></scrbytes></script>
            </devicefile>
            """
        )
        session = NamedScriptSession(
            commands=Commands(ICD4CommsUsb(Ri4Com(FakeTransport()))),
            device_file=DeviceFile.from_xml_text("dsPIC30F5011", xml),
            processor="dsPIC30F5011",
            family="DSPIC30F",
        )

        attempts = {"speed": 0}
        seen = []

        def fake_run_script(name, *params, timeout_ms=-1):
            seen.append(name)
            if name == "SetSpeedFromDevice":
                attempts["speed"] += 1
                if attempts["speed"] == 1:
                    raise RuntimeError("transient speed selection failure")
            return {"script": name, "status": 0, "payloadHex": ""}

        session.run_script = fake_run_script  # type: ignore[method-assign]

        result = session.enter_programming_mode()

        self.assertEqual(seen, ["SetSpeedFromDevice", "SetSpeedFromDevice", "EnterTMOD_HV"])
        self.assertEqual(result["script"], "EnterTMOD_HV")

    def test_enter_programming_mode_precleans_scripting_engine(self):
        xml = textwrap.dedent(
            """
            <devicefile>
              <processor>dsPIC30F5011</processor>
              <script><function>SetSpeedFromDevice</function><scrbytes><byte>0xEC</byte></scrbytes></script>
              <script><function>EnterTMOD_HV</function><scrbytes><byte>0xB6</byte></scrbytes></script>
            </devicefile>
            """
        )
        comm = ICD4CommsUsb(Ri4Com(FakeTransport()))
        calls = []
        comm.abort_scripting_engine = lambda timeout_ms=None: calls.append("abort") or b""  # type: ignore[method-assign]
        session = NamedScriptSession(
            commands=Commands(comm),
            device_file=DeviceFile.from_xml_text("dsPIC30F5011", xml),
            processor="dsPIC30F5011",
            family="DSPIC30F",
        )

        session.run_script = lambda name, *params, timeout_ms=-1: calls.append(name) or {  # type: ignore[method-assign]
            "script": name,
            "status": 0,
            "payloadHex": "",
        }

        session.enter_programming_mode()

        self.assertEqual(calls, ["abort", "SetSpeedFromDevice", "EnterTMOD_HV"])

    def test_named_script_session_executes_named_upload(self):
        xml = textwrap.dedent(
            """
            <devicefile>
              <processor>PIC16F_TEST</processor>
              <script>
                <function>GetPC</function>
                <scrbytes><byte>0xAA</byte><byte>0x55</byte></scrbytes>
              </script>
            </devicefile>
            """
        )
        device_file = DeviceFile.from_xml_text("PIC16F_TEST", xml)

        side_out = 0x02
        side_in = 0x81
        data_in = 0x83
        transport = None
        state = {"phase": 0}

        def on_send(ep: int, data: bytes, timeout_ms: int):
            if ep != side_out or len(data) < 16:
                return
            msg_type = _u32le(data)
            if msg_type == (ICD4CommsUsb.SCRIPT_WITH_UPLOAD & 0xFFFFFFFF):
                transport.queue_recv(side_in, _ack_ok())
                transport.queue_recv(data_in, b"\x34\x12")
                state["phase"] = 1
            elif msg_type == (ICD4CommsUsb.SCRDONE & 0xFFFFFFFF) and state["phase"] == 1:
                transport.queue_recv(side_in, _result_ok())

        transport = FakeTransport(on_send=on_send)
        session = NamedScriptSession(
            commands=Commands(ICD4CommsUsb(Ri4Com(transport))),
            device_file=device_file,
            processor="PIC16F_TEST",
            pc_bytes=2,
        )

        result = session.get_pc()
        self.assertEqual(result["pc"], 0x1234)
        self.assertEqual(result["rawHex"], "3412")

    def test_profile_selects_pe_programming_script(self):
        xml = textwrap.dedent(
            """
            <devicefile>
              <processor>DSPIC33FJ128GP</processor>
              <script><function>WriteProgmemPE</function><scrbytes><byte>0x01</byte></scrbytes></script>
              <script><function>ReadProgmemPE</function><scrbytes><byte>0x02</byte></scrbytes></script>
              <script><function>EraseChip</function><scrbytes><byte>0x03</byte></scrbytes></script>
            </devicefile>
            """
        )
        session = NamedScriptSession(
            commands=Commands(ICD4CommsUsb(Ri4Com(FakeTransport()))),
            device_file=DeviceFile.from_xml_text("DSPIC33FJ128GP", xml),
            processor="DSPIC33FJ128GP",
            family="DSPIC33FJ",
        )
        self.assertEqual(session.profile, get_family_profile("DSPIC33FJ"))
        seen = []
        session.run_script_with_download = lambda name, data, *params, timeout_ms=-1: seen.append((name, timeout_ms)) or {  # type: ignore[method-assign]
            "script": name,
            "status": 0,
            "payloadHex": "",
        }
        session.write_program(0x100, b"\x01\x02")
        self.assertEqual(seen, [("WriteProgmemPE", NamedScriptSession.PROGRAM_SCRIPT_TIMEOUT_MS)])

    def test_program_hex_uses_erase_write_and_verify_scripts(self):
        xml = textwrap.dedent(
            """
            <devicefile>
              <processor>PIC18F_TEST</processor>
              <script><function>EraseChip</function><scrbytes><byte>0x01</byte></scrbytes></script>
              <script><function>WriteProgmem</function><scrbytes><byte>0x02</byte></scrbytes></script>
              <script><function>ReadProgmem</function><scrbytes><byte>0x03</byte></scrbytes></script>
            </devicefile>
            """
        )
        device_file = DeviceFile.from_xml_text("PIC18F_TEST", xml)
        writes = []

        session = NamedScriptSession(
            commands=Commands(ICD4CommsUsb(Ri4Com(FakeTransport()))),
            device_file=device_file,
            processor="PIC18F_TEST",
            family="PIC18",
        )

        session.erase_chip = lambda mode=None: {"script": "EraseChip", "status": 0}  # type: ignore[method-assign]
        session.write_program = lambda address, data, script_name="WriteProgmem": writes.append((address, data)) or {  # type: ignore[method-assign]
            "script": script_name,
            "status": 0,
        }
        session.run_script_with_upload = lambda name, expected_length, address, length: writes[-1][1]  # type: ignore[method-assign]

        with tempfile.TemporaryDirectory() as tmpdir:
            hex_path = Path(tmpdir) / "blink.hex"
            hex_path.write_text(":0400000001020304F2\n:00000001FF\n", encoding="utf-8")
            result = session.program_hex(str(hex_path), erase_first=True, verify=True)

        self.assertEqual(result["segmentCount"], 1)
        self.assertEqual(result["segments"][0]["address"], 0)
        self.assertEqual(result["segments"][0]["size"], 4)
        self.assertEqual(writes, [(0, b"\x01\x02\x03\x04")])

    def test_dspic30f_read_program_range_clamps_chunk_size_to_family_limit(self):
        xml = textwrap.dedent(
            """
            <devicefile>
              <processor>dsPIC30F5011</processor>
              <script><function>ReadProgmem</function><scrbytes><byte>0x01</byte></scrbytes></script>
            </devicefile>
            """
        )
        session = NamedScriptSession(
            commands=Commands(ICD4CommsUsb(Ri4Com(FakeTransport()))),
            device_file=DeviceFile.from_xml_text("dsPIC30F5011", xml),
            processor="dsPIC30F5011",
            family="DSPIC30F",
        )

        reads = []

        def fake_read_program(address: int, length: int, script_name: str = "ReadProgmem"):
            reads.append((address, length))
            return {
                "address": address,
                "length": length,
                "dataHex": (b"\x00" * length).hex(),
                "script": script_name,
            }

        session.read_program = fake_read_program  # type: ignore[method-assign]

        image = session.read_program_range(0, 64, chunk_size=64)

        self.assertEqual(reads, [(0, 60), (40, 60)])
        self.assertEqual(len(image.segments), 2)
        self.assertEqual(len(image.segments[1].data), 4)

    def test_dump_program_hex_reports_effective_chunk_size(self):
        xml = textwrap.dedent(
            """
            <devicefile>
              <processor>dsPIC30F5011</processor>
              <script><function>ReadProgmem</function><scrbytes><byte>0x01</byte></scrbytes></script>
            </devicefile>
            """
        )
        session = NamedScriptSession(
            commands=Commands(ICD4CommsUsb(Ri4Com(FakeTransport()))),
            device_file=DeviceFile.from_xml_text("dsPIC30F5011", xml),
            processor="dsPIC30F5011",
            family="DSPIC30F",
        )
        session.enter_programming_mode = lambda: {"script": "EnterTMOD_HV", "status": 0}  # type: ignore[method-assign]
        session.exit_programming_mode = lambda: {"script": "ExitTMOD", "status": 0}  # type: ignore[method-assign]
        session.read_program_range = lambda start_address, length, chunk_size=64: FirmwareImage(  # type: ignore[method-assign]
            segments=(Segment(address=start_address, data=b"\x00" * length),)
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            hex_path = Path(tmpdir) / "dump.hex"
            result = session.dump_program_hex(str(hex_path), start_address=0, length=64, chunk_size=64)

        self.assertEqual(result["chunkSize"], 64)
        self.assertEqual(result["effectiveChunkSize"], 60)

    def test_run_first_with_upload_named_does_not_retry_with_empty_secondary_params(self):
        xml = textwrap.dedent(
            """
            <devicefile>
              <processor>dsPIC30F5011</processor>
              <script><function>ReadProgmem</function><scrbytes><byte>0x01</byte></scrbytes></script>
            </devicefile>
            """
        )
        session = NamedScriptSession(
            commands=Commands(ICD4CommsUsb(Ri4Com(FakeTransport()))),
            device_file=DeviceFile.from_xml_text("dsPIC30F5011", xml),
            processor="dsPIC30F5011",
            family="DSPIC30F",
        )

        calls = []

        def fake_run_script_with_upload(name: str, expected_length: int, *params):
            calls.append((name, expected_length, params))
            raise RuntimeError("fail once")

        session.run_script_with_upload = fake_run_script_with_upload  # type: ignore[method-assign]

        with self.assertRaises(RuntimeError):
            session.run_first_with_upload_named(("ReadProgmem",), 60, (0, 60))

        self.assertEqual(calls, [("ReadProgmem", 60, (0, 60))])
    def test_program_hex_exits_programming_mode_after_write_failure(self):
        xml = """
        <devicefile>
          <processor>PIC18F_TEST</processor>
          <script><function>EnterTMOD_LV</function><scrbytes><byte>0x01</byte></scrbytes></script>
          <script><function>ExitTMOD</function><scrbytes><byte>0x02</byte></scrbytes></script>
          <script><function>WriteProgmem</function><scrbytes><byte>0x03</byte></scrbytes></script>
        </devicefile>
        """
        session = NamedScriptSession(
            commands=Commands(ICD4CommsUsb(Ri4Com(FakeTransport()))),
            device_file=DeviceFile.from_xml_text("PIC18F_TEST", xml),
            processor="PIC18F_TEST",
            family="PIC18",
        )
        calls = []
        session.enter_programming_mode = lambda: calls.append("enter") or {"script": "EnterTMOD_LV"}  # type: ignore[method-assign]
        session.exit_programming_mode = lambda: calls.append("exit") or {"script": "ExitTMOD"}  # type: ignore[method-assign]

        def fail_write(address, data, script_name="WriteProgmem"):
            raise RuntimeError("write failed")

        session.write_program = fail_write  # type: ignore[method-assign]

        with tempfile.TemporaryDirectory() as tmpdir:
            hex_path = Path(tmpdir) / "broken.hex"
            hex_path.write_text(":0400000001020304F2\n:00000001FF\n", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "write failed"):
                session.program_hex(str(hex_path), erase_first=False)

        self.assertEqual(calls, ["enter", "exit"])

    def test_program_hex_chunks_using_family_program_address_geometry(self):
        xml = """
        <devicefile>
          <processor>dsPIC30F5011</processor>
          <script><function>WriteProgmem</function><scrbytes><byte>0x01</byte></scrbytes></script>
        </devicefile>
        """
        session = NamedScriptSession(
            commands=Commands(ICD4CommsUsb(Ri4Com(FakeTransport()))),
            device_file=DeviceFile.from_xml_text("dsPIC30F5011", xml),
            processor="dsPIC30F5011",
            family="DSPIC30F",
        )
        writes = []
        session.write_program = lambda address, data, script_name="WriteProgmem": writes.append((address, data)) or {"script": "WriteProgmem"}  # type: ignore[method-assign]

        with tempfile.TemporaryDirectory() as tmpdir:
            hex_path = Path(tmpdir) / "dspic.hex"
            hex_path.write_text(":0C000000000102030405060708090A0BB2\n:00000001FF\n", encoding="utf-8")
            result = session.program_hex(str(hex_path), erase_first=False, chunk_size=6)

        self.assertEqual([address for address, _ in writes], [0, 4])
        self.assertEqual([len(data) for _, data in writes], [6, 6])
        self.assertEqual(result["segments"][0]["chunks"], 2)

    def test_get_halt_status_and_post_halt_transition(self):
        xml = """
        <devicefile>
          <processor>PIC18F_TEST</processor>
          <script><function>GetHaltStatus</function><scrbytes><byte>0x01</byte></scrbytes></script>
          <script><function>PostHalt</function><scrbytes><byte>0x02</byte></scrbytes></script>
        </devicefile>
        """
        session = NamedScriptSession(
            commands=Commands(ICD4CommsUsb(Ri4Com(FakeTransport()))),
            device_file=DeviceFile.from_xml_text("PIC18F_TEST", xml),
            processor="PIC18F_TEST",
            family="PIC18",
        )
        post_halt_calls = []

        def fake_run(name, *params, timeout_ms=-1):
            if name == "PostHalt":
                post_halt_calls.append(name)
                return {"script": name, "status": 0, "payloadHex": ""}
            return {"script": name, "status": 0, "payloadHex": "aaaaaaaa"}

        session.run_script = fake_run  # type: ignore[method-assign]
        first = session.is_running()
        second = session.is_running()

        self.assertFalse(first["running"])
        self.assertEqual(first["state"], "halted")
        self.assertFalse(second["running"])
        self.assertEqual(post_halt_calls, ["PostHalt"])

    def test_avr_hardware_breakpoint_and_watchpoint_scripts(self):
        xml = """
        <devicefile>
          <processor>ATXMEGA_TEST</processor>
          <script><function>SetHWBP</function><scrbytes><byte>0x01</byte></scrbytes></script>
          <script><function>SetDataHWBP</function><scrbytes><byte>0x02</byte></scrbytes></script>
          <script><function>ClearHWBP</function><scrbytes><byte>0x03</byte></scrbytes></script>
        </devicefile>
        """
        session = NamedScriptSession(
            commands=Commands(ICD4CommsUsb(Ri4Com(FakeTransport()))),
            device_file=DeviceFile.from_xml_text("ATXMEGA_TEST", xml),
            processor="ATXMEGA_TEST",
            family="AVR",
        )
        calls = []
        session.run_script = lambda name, *params, timeout_ms=-1: calls.append((name, params)) or {"script": name, "status": 0, "payloadHex": ""}  # type: ignore[method-assign]

        bp = session.add_breakpoint(0x100)
        wp = session.add_watchpoint(0x200, access="write")
        session.remove_breakpoint(0x100, slot=bp["slot"])
        session.remove_watchpoint(0x200, slot=wp["slot"])

        self.assertEqual(calls[0], ("SetHWBP", (0, 0x100)))
        self.assertEqual(calls[1][0], "SetDataHWBP")
        self.assertEqual(calls[2], ("ClearHWBP", (0,)))
        self.assertEqual(calls[3], ("ClearHWBP", (1,)))
