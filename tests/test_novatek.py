"""Validate the actual patch payload and board selection, without hardware."""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import mkadt


class Novatek(unittest.TestCase):
    def test_explicit_selection_never_embeds_focaltech_firmware(self):
        with patch.object(mkadt, "d22ap_product", return_value=[]):
            tree = mkadt.build(
                device="joyeuse", product="fixture", touch_controller="none"
            )
            chosen = next(n for n in tree.children if n.name == "chosen")
            self.assertEqual(chosen.prop("sweet-touch-controller"), b"none\0")
            self.assertNotIn("focaltech-firmware", [k for k, _, _ in chosen.props])
            with self.assertRaisesRegex(ValueError, "explicit permutation"):
                mkadt.build(
                    device="joyeuse", product="fixture", touch_controller="novatek"
                )
            with self.assertRaisesRegex(ValueError, "touch-firmware"):
                mkadt.build(device="joyeuse", product="fixture")

    def test_patch_applies_and_decoder_handles_contacts(self):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            subprocess.run(
                [
                    "git",
                    "apply",
                    "--whitespace=nowarn",
                    "--include=bsd/dev/sweet_touch.c",
                    "--include=bsd/dev/sweet_novatek.h",
                    "--include=bsd/dev/sweet_novatek_spi.inc",
                    *map(str, sorted((ROOT / "xnu/patches").glob("*.patch"))),
                ],
                cwd=work,
                check=True,
                capture_output=True,
            )
            binary = work / ("novatek.exe" if os.name == "nt" else "novatek")
            compiler = (
                [os.environ["ZIG"], "cc"]
                if "ZIG" in os.environ
                else [os.environ.get("CC", "cc")]
            )
            subprocess.run(
                compiler
                + [
                    "-std=c11",
                    "-Wall",
                    "-Wextra",
                    "-Werror",
                    "-I",
                    str(work / "bsd/dev"),
                    str(ROOT / "tests/novatek_host.c"),
                    "-o",
                    str(binary),
                ],
                check=True,
                capture_output=True,
            )
            subprocess.run([str(binary)], check=True, capture_output=True)
            subprocess.run(
                compiler
                + [
                    "-std=c11",
                    "-Wall",
                    "-Wextra",
                    "-Werror",
                    "-I",
                    str(work / "bsd/dev"),
                    str(ROOT / "tests/novatek_spi_host.c"),
                    "-o",
                    str(binary),
                ],
                check=True,
                capture_output=True,
            )
            subprocess.run([str(binary)], check=True, capture_output=True)


if __name__ == "__main__":
    unittest.main()
