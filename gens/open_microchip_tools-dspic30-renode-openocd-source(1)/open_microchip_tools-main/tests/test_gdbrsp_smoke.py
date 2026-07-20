import socketserver
import threading
import time
import unittest

from mchp_gdbrsp import GdbRemoteClient
from mchp_gdbrsp.rsp import encode_packet


class _FakeOpenOcdHandler(socketserver.BaseRequestHandler):
    def handle(self):
        self.request.settimeout(0.5)

        # Deterministic memory image.
        mem = bytes(range(256))

        def send_packet(payload: bytes):
            self.request.sendall(b"+")
            self.request.sendall(encode_packet(payload))

        buf = bytearray()
        last_rx = time.time()
        while True:
            try:
                data = self.request.recv(4096)
            except TimeoutError:
                if time.time() - last_rx > 2.0:
                    return
                continue
            if not data:
                return
            last_rx = time.time()
            buf.extend(data)

            # ignore ctrl-c
            while b"\x03" in buf:
                buf.remove(0x03)

            # Parse packets in a very small, permissive way (test server).
            while True:
                if b"$" not in buf:
                    break
                start = buf.index(ord("$"))
                if start:
                    del buf[:start]
                if b"#" not in buf:
                    break
                hash_idx = buf.index(ord("#"))
                if len(buf) < hash_idx + 3:
                    break
                payload = bytes(buf[1:hash_idx])
                del buf[: hash_idx + 3]

                # Client will send ack '+' after our reply packet; ignore it.
                payload_str = payload.decode("ascii", errors="replace")

                if payload_str.startswith("qSupported"):
                    send_packet(b"PacketSize=4000;QStartNoAckMode+")
                elif payload_str == "QStartNoAckMode":
                    # Client switches to no-ack after OK.
                    send_packet(b"OK")
                elif payload_str.startswith("m"):
                    # mADDR,LEN (hex)
                    body = payload_str[1:]
                    a_s, l_s = body.split(",", 1)
                    addr = int(a_s, 16)
                    ln = int(l_s, 16)
                    send_packet(mem[addr : addr + ln].hex().encode("ascii"))
                elif payload_str.startswith("M"):
                    # Always OK
                    send_packet(b"OK")
                elif payload_str[:1] in ("Z", "z"):
                    send_packet(b"OK")
                elif payload_str in ("c", "s"):
                    # Immediately stop (SIGTRAP)
                    send_packet(b"S05")
                else:
                    send_packet(b"")


class _ThreadingTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


class TestGdbRspSmoke(unittest.TestCase):
    def test_handshake_and_memory_read(self):
        with _ThreadingTCPServer(("127.0.0.1", 0), _FakeOpenOcdHandler) as srv:
            t = threading.Thread(target=srv.serve_forever, daemon=True)
            t.start()
            host, port = srv.server_address
            try:
                with GdbRemoteClient(host=host, port=port, try_no_ack=True, timeout=2.0) as c:
                    caps = c.qSupported()
                    self.assertIn("PacketSize", caps)
                    data = c.read_memory(0x10, 16)
                    self.assertEqual(data, bytes(range(0x10, 0x20)))
                    c.write_memory(0x00, b"\x01\x02")
                    self.assertTrue(c.set_hw_breakpoint(0x1234, kind=2))
                    self.assertTrue(c.set_write_watchpoint(0x2000, length=4))
                    self.assertTrue(c.set_read_watchpoint(0x2000, length=4))
                    self.assertTrue(c.set_access_watchpoint(0x2000, length=4))
                    self.assertTrue(c.clear_hw_breakpoint(0x1234, kind=2))
                    self.assertTrue(c.clear_write_watchpoint(0x2000, length=4))
                    stop = c.step()
                    self.assertEqual(stop.kind, "S")
                    self.assertEqual(stop.signal, 5)
            finally:
                srv.shutdown()
                srv.server_close()
                t.join(timeout=2.0)

    def test_breakpoint_packet_validation(self):
        client = GdbRemoteClient()
        with self.assertRaisesRegex(ValueError, "range 0..4"):
            client.insert_breakpoint(5, 0x100, 1)
        with self.assertRaisesRegex(ValueError, "positive"):
            client.remove_breakpoint(1, 0x100, 0)


if __name__ == "__main__":
    unittest.main()
