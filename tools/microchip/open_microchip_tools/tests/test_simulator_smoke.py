import unittest


class TestSimulatorSmoke(unittest.TestCase):
    def test_legacy_import_and_basic_flow(self):
        from com.microchip.mplab.mdbcore.simulator.Simulator import Simulator
        from mchp_mdbcore.simulator import MEMTYPE

        sim = Simulator()
        sim.Engage(object())
        self.assertTrue(sim.ConnectToTool(None))

        sim.SetPC(0x10)
        self.assertEqual(sim.GetPC(), 0x10)

        # Single step increments PC
        sim.SingleStepTarget()
        self.assertEqual(sim.GetPC(), 0x11)

        # Memory read/write
        payload = b"\x01\x02\x03\x04"
        written = sim.WriteTargetMemory(MEMTYPE.PROGRAM_MEMORY, 0x100, len(payload), payload)
        self.assertEqual(written, len(payload))

        out = bytearray(len(payload))
        read = sim.ReadTargetMemory(MEMTYPE.PROGRAM_MEMORY, 0x100, len(payload), out)
        self.assertEqual(read, len(payload))
        self.assertEqual(bytes(out), payload)

    def test_observers_and_code_coverage(self):
        from mchp_mdbcore.simulator import Simulator, ToolEvent

        events = []

        def on_event(e):
            events.append(e)

        sim = Simulator()
        sim.Attach(on_event, None)
        sim.Engage(object())

        sim.startCodeCoverage()
        sim.processor.halt_after_steps = 3
        sim.RunTarget()
        sim.stopCodeCoverage()

        cov = sim.retrieveCodeCoverage()
        self.assertTrue(len(cov) >= 1)
        self.assertTrue(any(v >= 1 for v in cov.values()))
        self.assertTrue(any(e == ToolEvent.EVENTS.RUN for e in events))
        self.assertTrue(any(e == ToolEvent.EVENTS.HALT for e in events))

    def test_stub_importer_allows_deep_imports(self):
        # These classes exist in Java but are not implemented in this clean-room port.
        from com.microchip.mplab.mdbcore.simulator.pic32.Helper import Helper

        with self.assertRaises(NotImplementedError):
            Helper()


if __name__ == "__main__":
    unittest.main()
