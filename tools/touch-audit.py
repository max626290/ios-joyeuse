"""Read-only Android touch inventory. Does not open raw SPI or reboot the phone.

Use before selecting a hardware touch driver: joyeuse boards can differ.
Output belongs in logs/ (ignored by Git). ADB must already be authorized.
"""

import argparse
import json
import re
import subprocess
from pathlib import Path


def classify(events):
    names = re.findall(r'name:\s*"([^"]+)"', events)
    if "NVTCapacitiveTouchScreen" in names:
        return {
            "family": "Novatek",
            "chip": None,
            "ft8756_driver_compatible": False,
            "reason": "Android exposes NVTCapacitiveTouchScreen; exact chip is not encoded in that name.",
        }
    return {
        "family": "unknown",
        "chip": None,
        "ft8756_driver_compatible": None,
        "reason": "No recognized Novatek input name. This does not confirm FocalTech.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adb", default="adb")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    subprocess.run([args.adb, "get-state"], check=True, capture_output=True, timeout=10)
    probes = {
        "device": "getprop ro.product.device",
        "firmware": "getprop ro.build.version.incremental",
        "bootloader_locked": "getprop ro.boot.flash.locked",
        "input_devices": "getevent -lp",
        "touch_info": "cat /proc/tp_info",
        "lockdown_info": "cat /proc/tp_lockdown_info",
        "novatek_firmware_version": "cat /proc/nvt_fw_version",
        "spi_modalias": "cat /sys/bus/spi/devices/spi0.1/modalias /sys/bus/spi/devices/spi1.0/modalias",
    }
    evidence = {}
    for name, command in probes.items():
        try:
            result = subprocess.run(
                [args.adb, "shell", command], capture_output=True,
                text=True, encoding="utf-8", errors="replace", timeout=15,
            )
            evidence[name] = {
                "command": command, "returncode": result.returncode,
                "stdout": result.stdout.strip(), "stderr": result.stderr.strip(),
            }
        except subprocess.TimeoutExpired:
            evidence[name] = {"command": command, "error": "timeout"}
    events = evidence["input_devices"].get("stdout", "")
    report = {
        "schema": 1, "read_only": True,
        "assessment": classify(events), "evidence": evidence,
        "limitations": [
            "Permission denied is missing evidence, not missing hardware.",
            "Family detection cannot establish chip ID, firmware choice, GPIO routing or successful iOS operation.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report["assessment"], ensure_ascii=False))
    print(f"Evidence saved to {args.output}")


if __name__ == "__main__":
    main()
