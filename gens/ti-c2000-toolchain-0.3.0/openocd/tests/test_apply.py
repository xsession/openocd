from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

BUNDLE = Path(__file__).resolve().parents[1]
APPLIER = BUNDLE / "scripts/apply_xds100_support.py"
FIXTURE = BUNDLE / "tests/fixtures/ftdi.c"
LEGACY_FIXTURE = BUNDLE / "tests/fixtures/ftdi-legacy.c"


class ApplyTests(unittest.TestCase):
    def make_repo(self, base: Path, fixture: Path = FIXTURE) -> Path:
        repo = base / "openocd"
        target = repo / "src/jtag/drivers/ftdi.c"
        target.parent.mkdir(parents=True)
        shutil.copy2(fixture, target)
        (repo / "contrib").mkdir()
        (repo / "contrib/60-openocd.rules").write_text(
            '# XDS100v2\nATTRS{idVendor}=="0403", ATTRS{idProduct}=="a6d0", MODE="660", GROUP="plugdev", TAG+="uaccess"\n',
            encoding="utf-8",
        )
        return repo

    def run_tool(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(APPLIER), *args],
            check=False,
            text=True,
            capture_output=True,
        )

    def test_apply_and_check(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo = self.make_repo(Path(temp))
            result = self.run_tool(str(repo))
            self.assertEqual(result.returncode, 0, result.stderr)

            source = (repo / "src/jtag/drivers/ftdi.c").read_text(encoding="utf-8")
            self.assertIn("struct ftdi_initial_signal", source)
            self.assertIn("ftdi_handle_initial_signal_command", source)
            self.assertIn('.name = "initial_signal"', source)
            self.assertIn("for (struct ftdi_initial_signal *initial", source)
            self.assertTrue((repo / "tcl/interface/ftdi/xds100v2.cfg").is_file())
            self.assertTrue((repo / "tcl/interface/ftdi/xds100v3.cfg").is_file())
            self.assertTrue((repo / "examples/c2000/tms320f28069-xds100v2.cfg").is_file())
            self.assertTrue((repo / "examples/c2000/tms320f280049-xds100v3.cfg").is_file())
            self.assertTrue((repo / "examples/c2000/tms320f28m35x-xds100v2.cfg").is_file())
            self.assertIn("mpsse_flush(mpsse_ctx)", source)
            self.assertIn('idProduct}=="a6d1"', (repo / "contrib/60-openocd.rules").read_text())

            check = self.run_tool(str(repo), "--check")
            self.assertEqual(check.returncode, 0, check.stderr)

    def test_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo = self.make_repo(Path(temp))
            first = self.run_tool(str(repo))
            self.assertEqual(first.returncode, 0, first.stderr)
            once = (repo / "src/jtag/drivers/ftdi.c").read_text(encoding="utf-8")
            second = self.run_tool(str(repo))
            self.assertEqual(second.returncode, 0, second.stderr)
            twice = (repo / "src/jtag/drivers/ftdi.c").read_text(encoding="utf-8")
            self.assertEqual(once, twice)

    def test_dry_run_does_not_modify(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo = self.make_repo(Path(temp))
            before = (repo / "src/jtag/drivers/ftdi.c").read_text(encoding="utf-8")
            result = self.run_tool(str(repo), "--dry-run")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("ftdi_initial_signal", result.stdout)
            after = (repo / "src/jtag/drivers/ftdi.c").read_text(encoding="utf-8")
            self.assertEqual(before, after)

    def test_legacy_cleanup_layout(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo = self.make_repo(Path(temp), LEGACY_FIXTURE)
            result = self.run_tool(str(repo))
            self.assertEqual(result.returncode, 0, result.stderr)
            source = (repo / "src/jtag/drivers/ftdi.c").read_text(encoding="utf-8")
            self.assertIn("ftdi_initial_signals = NULL", source)

    def test_patched_fixture_compiles(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo = self.make_repo(Path(temp))
            result = self.run_tool(str(repo))
            self.assertEqual(result.returncode, 0, result.stderr)
            compile_result = subprocess.run(
                ["gcc", "-std=gnu11", "-Wall", "-Wextra", "-Wno-unused-parameter",
                 "-fsyntax-only", str(repo / "src/jtag/drivers/ftdi.c")],
                check=False, text=True, capture_output=True,
            )
            self.assertEqual(compile_result.returncode, 0, compile_result.stderr)


if __name__ == "__main__":
    unittest.main()
