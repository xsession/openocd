import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mchp_ipecmd.programmer_cli import ProgramRequest, ProgrammerCliError, build_ipecmd_command, main


class TestPk4ProgrammerCli(unittest.TestCase):
    def test_build_ipecmd_command_reports_repo_only_limit(self):
        request = ProgramRequest(
            hex_path=Path(r"C:\fw\app.hex"),
            device="PIC16F1509",
        )

        with self.assertRaises(ProgrammerCliError):
            build_ipecmd_command(request)

    def test_main_dry_run_prints_command(self):
        with tempfile.TemporaryDirectory() as td:
            hex_path = Path(td) / "blink.hex"
            hex_path.write_text(":00000001FF\n", encoding="ascii")
            stdout = io.StringIO()
            stderr = io.StringIO()

            with patch("mchp_ipecmd.programmer_cli.available_device_names", return_value=["PIC16F1509"]):
                code = main([str(hex_path), "--device", "pic16f1509", "--dry-run"], stdout=stdout, stderr=stderr)

        self.assertEqual(code, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("Repo-only hardware programming is not implemented yet", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()