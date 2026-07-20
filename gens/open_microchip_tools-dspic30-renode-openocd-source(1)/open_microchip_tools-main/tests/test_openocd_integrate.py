import tempfile
import unittest
from pathlib import Path

from mchp_openocd.integrate import (
    IntegrationError,
    apply_integration,
    integration_status,
    remove_integration,
)


class TestOpenOcdIntegrationInstaller(unittest.TestCase):
    def _checkout(self, root: Path) -> Path:
        (root / "src/target").mkdir(parents=True)
        (root / "src/flash/nor").mkdir(parents=True)
        (root / "tcl/interface").mkdir(parents=True)
        (root / "tcl/target").mkdir(parents=True)
        (root / "src/target/Makefile.am").write_text(
            "TARGET_CORE_SRC = \\\n\t%D%/target.c \\\n\t%D%/testee.c \\\n\t%D%/smp.c\n",
            encoding="utf-8",
        )
        (root / "src/target/target.c").write_text(
            "static struct target_type *target_types[] = {\n"
            "\t&mem_ap_target,\n\t&mips_m4k_target,\n};\n",
            encoding="utf-8",
        )
        (root / "src/target/target_type.h").write_text(
            "extern struct target_type mem_ap_target;\n"
            "extern struct target_type mips_m4k_target;\n",
            encoding="utf-8",
        )
        (root / "src/flash/nor/Makefile.am").write_text(
            "NOR_DRIVERS = \\\n"
            "\t%D%/mdr.c \\\n"
            "\t%D%/mrvlqspi.c\n",
            encoding="utf-8",
        )
        (root / "src/flash/nor/driver.h").write_text(
            "extern const struct flash_driver mdr_flash;\n"
            "extern const struct flash_driver mrvlqspi_flash;\n",
            encoding="utf-8",
        )
        (root / "src/flash/nor/drivers.c").write_text(
            "static const struct flash_driver * const flash_drivers[] = {\n"
            "\t&mdr_flash,\n\t&mrvlqspi_flash,\n};\n",
            encoding="utf-8",
        )
        return root

    def test_apply_is_idempotent_and_remove_restores_anchors(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            checkout = self._checkout(Path(tmpdir))
            first = apply_integration(checkout)
            second = apply_integration(checkout)

            self.assertIn("src/target/mchp_ri4_bridge.c", first)
            self.assertIn("src/flash/nor/mchp_ri4.c", first)
            self.assertEqual(second, [])
            status = integration_status(checkout)
            self.assertTrue(status["installed"])
            self.assertIn("mchp_ri4_bridge_target", (checkout / "src/target/target.c").read_text())
            self.assertIn("mchp_ri4_flash", (checkout / "src/flash/nor/drivers.c").read_text())

            removed = remove_integration(checkout)
            self.assertIn("src/target/mchp_ri4_bridge.c", removed)
            self.assertFalse((checkout / "src/target/mchp_ri4_bridge.c").exists())
            self.assertFalse((checkout / "src/flash/nor/mchp_ri4.c").exists())
            self.assertNotIn("mchp_ri4_bridge_target", (checkout / "src/target/target.c").read_text())

    def test_dry_run_does_not_modify_checkout(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            checkout = self._checkout(Path(tmpdir))
            changed = apply_integration(checkout, dry_run=True)
            self.assertTrue(changed)
            self.assertFalse((checkout / "src/target/mchp_ri4_bridge.c").exists())
            self.assertFalse((checkout / "src/flash/nor/mchp_ri4.c").exists())
            self.assertFalse(integration_status(checkout)["installed"])

    def test_changed_upstream_anchor_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            checkout = self._checkout(Path(tmpdir))
            (checkout / "src/target/target.c").write_text("layout changed\n", encoding="utf-8")
            with self.assertRaisesRegex(IntegrationError, "expected anchor"):
                apply_integration(checkout)


if __name__ == "__main__":
    unittest.main()
