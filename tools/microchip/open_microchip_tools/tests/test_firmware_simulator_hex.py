from __future__ import annotations

from mchp_simulator.device_catalog import guess_device_spec
from mchp_simulator.firmware_image import FirmwareImage
from mchp_simulator.firmware_simulator import FirmwareSimulator


def test_intel_hex_loader_basic() -> None:
    text = ":0400000001020304F2\n:00000001FF\n"
    img = FirmwareImage.from_intel_hex_text(text)
    assert len(img.segments) == 1
    seg = img.segments[0]
    assert seg.address == 0
    assert seg.data == bytes([1, 2, 3, 4])


def test_firmware_simulator_load_and_breakpoint() -> None:
    spec = guess_device_spec("dsPIC33EP32GP502")
    sim = FirmwareSimulator(spec)
    sim.Engage(None)

    img = FirmwareImage.from_intel_hex_text(":0400000001020304F2\n:00000001FF\n")
    sim.load_firmware(img)

    # Break at address 4 (pc increments by 2 per step for dsPIC33 spec).
    sim.set_breakpoint(4)
    sim.RunTarget(max_steps=10)

    assert sim.GetPC() == 4
    trace = sim.get_trace(limit=10)
    assert trace
