import unittest

from mchp_ipecmd.client import IpecmdClient
from mchp_ipecmd.server import IpecmdServer


class TestIpecmdSocketSmoke(unittest.TestCase):
    def test_round_trip_ping(self):
        with IpecmdServer(host="127.0.0.1", port=0) as srv:
            client = IpecmdClient(host="127.0.0.1", port=srv.port)
            res = client.send(["PING"])

        self.assertEqual(res.error_code, 0)
        self.assertIn("EVENT:PONG", res.lines)
        self.assertIn("PONG", res.lines)
        self.assertIn("Operation Succeeded", res.lines)

    def test_round_trip_fail(self):
        with IpecmdServer(host="127.0.0.1", port=0) as srv:
            client = IpecmdClient(host="127.0.0.1", port=srv.port)
            res = client.send(["FAIL", "5"])

        self.assertEqual(res.error_code, 5)
        self.assertIn("Operation Failed (5)", res.lines)
        self.assertNotIn("Operation Succeeded", res.lines)

    def test_legacy_boost_client_import(self):
        with IpecmdServer(host="127.0.0.1", port=0) as srv:
            from com.microchip.mplab.ipecmdboost import Client as BoostClient

            bc = BoostClient(portNumber=srv.port, boostCmdString=["ECHO", "hello", "world"], hostName="127.0.0.1")
            res = bc.run()

        self.assertEqual(res.error_code, 0)
        self.assertIn("hello world", res.lines)


if __name__ == "__main__":
    unittest.main()
