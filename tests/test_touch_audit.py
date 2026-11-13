"""Never infer an exact controller or FocalTech compatibility from absent evidence."""

import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "touch_audit", Path(__file__).resolve().parents[1] / "tools" / "touch-audit.py"
)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class TouchAudit(unittest.TestCase):
    def test_novatek_does_not_imply_exact_chip(self):
        result = audit.classify('add device 4: /dev/input/event3\n  name: "NVTCapacitiveTouchScreen"')
        self.assertEqual(result["family"], "Novatek")
        self.assertIsNone(result["chip"])
        self.assertIs(result["ft8756_driver_compatible"], False)

    def test_missing_or_other_devices_do_not_confirm_focaltech(self):
        for text in ("", "Permission denied", 'name: "gpio-keys"', 'name: "fts"'):
            with self.subTest(text=text):
                self.assertIsNone(audit.classify(text)["ft8756_driver_compatible"])


if __name__ == "__main__":
    unittest.main()
