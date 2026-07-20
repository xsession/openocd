from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from ti_svd.cli import main
from ti_svd.cmsis import build_svd, write_svd
from ti_svd.config import load_manifest, repository_root
from ti_svd.models import Field, Peripheral, Register
from ti_svd.tixml import parse_device
from ti_svd.validate import validate_svd


class GeneratorTests(unittest.TestCase):
    def test_fixture_converts_and_scales_c28x_addresses(self) -> None:
        root = repository_root()
        targetdb = root / "tests" / "fixtures" / "targetdb"
        manifest = load_manifest("tms320f28069", root)
        peripherals = parse_device(targetdb / "devices" / "TMS320F28069.xml", targetdb, manifest)
        self.assertEqual([p.name for p in peripherals], ["GPIOA", "TIMER0"])
        self.assertEqual(peripherals[0].base_address, 0x2000)
        self.assertEqual(peripherals[0].registers[1].offset, 0x2)
        self.assertEqual(peripherals[0].registers[0].fields[0].name, "PIN0")
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / "test.svd"
            write_svd(build_svd(manifest, peripherals, "unit-test fixture"), destination)
            result = validate_svd(destination)
            self.assertTrue(result.ok, result.errors)
            self.assertEqual(result.peripheral_count, 2)
            self.assertEqual(result.register_count, 4)
            self.assertEqual(result.field_count, 3)

    def test_cortex_debug_profile_accepts_arm_svd(self) -> None:
        manifest = load_manifest("mspm0c1103")
        peripherals = [
            Peripheral(
                name="GPIOA",
                description="GPIO A",
                base_address=0x400A0000,
                registers=[
                    Register(
                        name="DOUT",
                        description="Data output",
                        offset=0,
                        size=32,
                        access="read-write",
                        fields=[Field("PIN0", "Pin zero", 0, 1)],
                    )
                ],
            )
        ]
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / "arm.svd"
            write_svd(build_svd(manifest, peripherals, "unit test"), destination)
            result = validate_svd(
                destination,
                require_cortex_debug=True,
                expected_core="CM0PLUS",
            )
            self.assertTrue(result.ok, result.errors)

    def test_cortex_debug_profile_rejects_c28x_svd(self) -> None:
        root = repository_root()
        targetdb = root / "tests" / "fixtures" / "targetdb"
        manifest = load_manifest("tms320f28069", root)
        peripherals = parse_device(targetdb / "devices" / "TMS320F28069.xml", targetdb, manifest)
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / "c28x.svd"
            write_svd(build_svd(manifest, peripherals, "unit-test fixture"), destination)
            result = validate_svd(destination, require_cortex_debug=True)
            self.assertFalse(result.ok)
            self.assertTrue(any("no <cpu><name>" in error for error in result.errors))

    def test_vscode_config_generates_c2000_debug_target(self) -> None:
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            status = main(["vscode-config", "tms320f28069"])
        self.assertEqual(status, 0)
        self.assertIn('"type": "c2000-debug"', stdout.getvalue())
        self.assertIn('"addressScale": 2', stdout.getvalue())
        self.assertIn('"backend": "ccs"', stdout.getvalue())

    def test_vscode_config_generates_renode_target(self) -> None:
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            status = main(["vscode-config", "tms320f28069", "--backend", "renode"])
        self.assertEqual(status, 0)
        generated = stdout.getvalue()
        self.assertIn('"backend": "renode"', generated)
        self.assertIn('"renodeMonitorPort": 1234', generated)
        self.assertIn('"registerProfile": "renode-c2000"', generated)

    def test_vscode_config_uses_current_svd_path_key(self) -> None:
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            status = main(["vscode-config", "mspm0c1103"])
        self.assertEqual(status, 0)
        self.assertIn('"svdPath"', stdout.getvalue())
        self.assertNotIn('"svdFile"', stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
