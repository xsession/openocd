#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later

"""Host-only tests for the Microchip programmer Tcl command bridge."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import textwrap
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
COMMON_TCL = REPO_ROOT / "tcl/programmer/microchip/common.tcl"
PROGRAMMER_DIR = REPO_ROOT / "tcl/programmer/microchip"


def tcl_quote(value: str | os.PathLike[str]) -> str:
    text = str(value)
    return "{" + text.replace("}", "\\}") + "}"


@unittest.skipUnless(shutil.which("tclsh"), "tclsh is required")
class MicrochipProgrammerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory(prefix="openocd-microchip-")
        self.addCleanup(self.tempdir.cleanup)
        self.firmware = Path(self.tempdir.name) / "firmware with spaces.hex"
        self.firmware.write_text(":020000040000FA\n:00000001FF\n", encoding="ascii")

    def run_tcl(self, body: str, expect_success: bool = True) -> subprocess.CompletedProcess[str]:
        script = textwrap.dedent(
            f"""
            source {tcl_quote(COMMON_TCL)}
            {body}
            """
        )
        result = subprocess.run(
            ["tclsh"],
            input=script,
            text=True,
            capture_output=True,
            check=False,
        )
        if expect_success and result.returncode != 0:
            self.fail(f"Tcl failed:\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}")
        return result

    def command(self, programmer: str, backend: str = "auto", extra: str = "") -> list[str]:
        result = self.run_tcl(
            f"""
            microchip programmer {programmer}
            microchip backend {backend}
            microchip device dsPIC33EP128GM604
            microchip executable fake-programmer
            {extra}
            set command [::microchip_programmer::build_command program {tcl_quote(self.firmware)}]
            puts "RESULT:[join $command |]"
            """
        )
        result_lines = [line for line in result.stdout.splitlines() if line.startswith("RESULT:")]
        self.assertEqual(len(result_lines), 1, result.stdout)
        return result_lines[0][len("RESULT:") :].split("|")

    def test_pickit2_pk2cmd_program_command(self) -> None:
        command = self.command("pickit2")
        self.assertEqual(command[0], "fake-programmer")
        self.assertIn("-PdsPIC33EP128GM604", command)
        self.assertIn(f"-F{self.firmware}", command)
        self.assertIn("-M", command)
        self.assertIn("-Y", command)
        self.assertIn("-L", command)

    def test_pickit3_defaults_to_ipecmd(self) -> None:
        command = self.command("pickit3")
        self.assertIn("-TPPK3", command)
        self.assertIn("-OL", command)

    def test_pickit3_can_use_pk2cmd(self) -> None:
        command = self.command("pickit3", "pk2cmd")
        self.assertIn("-L", command)
        self.assertNotIn("-TPPK3", command)

    def test_pickit4_ipecmd_command(self) -> None:
        command = self.command("pickit4", extra="microchip vdd 3.3")
        self.assertIn("-TPPK4", command)
        self.assertIn("-W3.3", command)
        self.assertIn("-E", command)
        self.assertIn("-OL", command)

    def test_icd4_serial_selection(self) -> None:
        command = self.command("icd4", extra="microchip serial BUR123456789")
        self.assertIn("-TSBUR123456789", command)
        self.assertNotIn("-TPICD4", command)

    def test_pymcuprog_is_explicit_and_limited_to_pickit4(self) -> None:
        command = self.command(
            "pickit4",
            "pymcuprog",
            "microchip interface updi\nmicrochip clock 100000",
        )
        self.assertEqual(
            command[:7],
            [
                "fake-programmer",
                "-t",
                "pickit4",
                "-d",
                "dsPIC33EP128GM604",
                "-i",
                "updi",
            ],
        )
        self.assertIn("write", command)
        self.assertIn("--erase", command)
        self.assertIn("--verify", command)

        result = self.run_tcl(
            """
            microchip programmer icd4
            microchip backend pymcuprog
            microchip device dsPIC33EP128GM604
            microchip executable fake-programmer
            if {![catch {::microchip_programmer::build_command erase ""} message]} {
                exit 2
            }
            puts stderr $message
            exit 1
            """,
            expect_success=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("PICkit 4", result.stderr)

    def test_external_backend_execution_preserves_arguments_and_cwd(self) -> None:
        backend_dir = Path(self.tempdir.name) / "backend directory"
        backend_dir.mkdir()
        log_file = Path(self.tempdir.name) / "backend.log"
        backend = backend_dir / "fake ipecmd"
        backend.write_text(
            "#!/bin/sh\n"
            "printf 'cwd=%s\\n' \"$PWD\" > \"$MICROCHIP_TEST_LOG\"\n"
            "printf 'arg=%s\\n' \"$@\" >> \"$MICROCHIP_TEST_LOG\"\n",
            encoding="ascii",
        )
        backend.chmod(0o755)
        result = self.run_tcl(
            f"""
            set ::env(MICROCHIP_TEST_LOG) {tcl_quote(log_file)}
            microchip programmer pickit4
            microchip device dsPIC33EP128GM604
            microchip executable {tcl_quote(backend)}
            microchip working_directory {tcl_quote(backend_dir)}
            microchip program {tcl_quote(self.firmware)}
            """
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        logged = log_file.read_text(encoding="utf-8").splitlines()
        self.assertEqual(logged[0], f"cwd={backend_dir}")
        self.assertIn("arg=-TPPK4", logged)
        self.assertIn(f"arg=-F{self.firmware}", logged)
        self.assertIn("arg=-OL", logged)

    def test_dry_run_does_not_execute_backend(self) -> None:
        result = self.run_tcl(
            f"""
            microchip programmer pickit4
            microchip device dsPIC33EP128GM604
            microchip executable definitely-not-an-executable
            microchip dry_run on
            microchip program {tcl_quote(self.firmware)}
            puts OK
            """
        )
        self.assertIn("OK", result.stdout)
        self.assertIn("definitely-not-an-executable", result.stdout)

    def test_all_programmer_presets_load(self) -> None:
        for name in ("pickit2", "pickit3", "pickit4", "icd4"):
            cfg = PROGRAMMER_DIR / f"{name}.cfg"
            script = textwrap.dedent(
                f"""
                proc noinit {{}} {{}}
                proc find {{relative}} {{ return [file join {tcl_quote(REPO_ROOT / 'tcl')} $relative] }}
                source {tcl_quote(cfg)}
                puts "RESULT:$::microchip_programmer::programmer"
                """
            )
            result = subprocess.run(
                ["tclsh"], input=script, text=True, capture_output=True, check=False
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(f"RESULT:{name}", result.stdout)

    def test_usb_identifiers_and_cmsis_dap_configs(self) -> None:
        rules = (REPO_ROOT / "contrib/60-openocd.rules").read_text(encoding="utf-8")
        self.assertIn('idVendor}=="04d8", ATTRS{idProduct}=="0033"', rules)
        self.assertIn('idVendor}=="04d8", ATTRS{idProduct}=="900a"', rules)
        self.assertIn('idVendor}=="03eb", ATTRS{idProduct}=="2177"', rules)
        self.assertIn('idVendor}=="03eb", ATTRS{idProduct}=="217c"', rules)

        pickit4 = (REPO_ROOT / "tcl/interface/microchip/pickit4-cmsis-dap.cfg").read_text()
        icd4 = (REPO_ROOT / "tcl/interface/microchip/icd4-cmsis-dap.cfg").read_text()
        self.assertIn("adapter usb vid_pid 0x03eb 0x2177", pickit4)
        self.assertIn("adapter usb vid_pid 0x03eb 0x217c", icd4)

class MicrochipLocalIntegrationTests(unittest.TestCase):
    def test_local_ri4_presets_and_launchers(self) -> None:
        pickit4 = (PROGRAMMER_DIR / "pickit4-ri4.cfg").read_text(encoding="utf-8")
        icd4 = (PROGRAMMER_DIR / "icd4-ri4.cfg").read_text(encoding="utf-8")
        self.assertIn("set MCHP_RI4_TOOL pk4", pickit4)
        self.assertIn("set MCHP_RI4_PID 0x9012", pickit4)
        self.assertIn("set MCHP_RI4_TOOL icd4", icd4)
        self.assertIn("set MCHP_RI4_PID 0x9036", icd4)
        self.assertIn("source [find target/mchp-ri4.cfg]", pickit4)
        self.assertIn("source [find target/mchp-ri4.cfg]", icd4)

        powershell = (REPO_ROOT / "scripts/start-microchip-ri4-bridge.ps1").read_text(
            encoding="utf-8"
        )
        shell = (REPO_ROOT / "scripts/start-microchip-ri4-bridge.sh").read_text(encoding="utf-8")
        self.assertIn("OPEN_MICROCHIP_TOOLS_ROOT", powershell)
        self.assertIn("mchp_openocd.bridge_server", powershell)
        self.assertIn("OPEN_MICROCHIP_TOOLS_ROOT", shell)
        self.assertIn("mchp_openocd.bridge_server", shell)

    def test_ri4_target_and_flash_drivers_are_registered(self) -> None:
        target_makefile = (REPO_ROOT / "src/target/Makefile.am").read_text(encoding="utf-8")
        target_types = (REPO_ROOT / "src/target/target_type.h").read_text(encoding="utf-8")
        flash_makefile = (REPO_ROOT / "src/flash/nor/Makefile.am").read_text(encoding="utf-8")
        flash_drivers = (REPO_ROOT / "src/flash/nor/drivers.c").read_text(encoding="utf-8")
        self.assertIn("%D%/mchp_ri4_bridge.c", target_makefile)
        self.assertIn("mchp_ri4_bridge_target", target_types)
        self.assertIn("%D%/mchp_ri4.c", flash_makefile)
        self.assertIn("&mchp_ri4_flash", flash_drivers)

    def test_generated_dspic_svds_are_present(self) -> None:
        svd_dir = REPO_ROOT / "svd"
        for name in (
            "dspic30f5011.svd",
            "dspic33fj128mc802.svd",
            "dspic33fj128mc804.svd",
            "dspic33ep128gm604.svd",
        ):
            text = (svd_dir / name).read_text(encoding="utf-8")
            self.assertIn("<device", text)
            self.assertIn("<peripherals>", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
