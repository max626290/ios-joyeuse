"""Windows/Linux device helper. Only userdata may be flashed; boot is RAM-only."""

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PARTITIONS = (
    "persist",
    "modemst1",
    "modemst2",
    "fsg",
    "fsc",
    "boot",
    "dtbo",
    "vbmeta",
    "modem",
)


def sha(path):
    with Path(path).open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def run(tool, *args):
    p = subprocess.run([str(tool), *args], capture_output=True, timeout=60, check=False)
    text = (p.stdout + p.stderr).decode("utf-8", errors="replace").strip()
    if p.returncode:
        raise RuntimeError(text)
    return text


def verify_file(base, entry):
    path = (base / entry["file"]).resolve()
    if not path.is_relative_to(base.resolve()):
        raise ValueError("file outside package")
    if path.stat().st_size != entry["size"] or sha(path) != entry["sha256"]:
        raise ValueError(f"invalid file hash/size: {path}")
    return path


def manifest_images(path):
    doc = json.loads(path.read_text())
    if doc.get("product") != "joyeuse" or doc.get("ready") is not True:
        raise ValueError("package is not ready for joyeuse")
    files = {k: verify_file(path.parent, doc[k]) for k in ("boot", "root")}
    with files["boot"].open("rb") as f:
        if f.read(8) != b"ANDROID!":
            raise ValueError("invalid boot image")
    with files["root"].open("rb") as f:
        if f.read(4) != b"\x3a\xff\x26\xed":
            raise ValueError("root must be Android sparse format")
    return files


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "action",
        choices=("status", "backup", "flash-root", "boot", "restore-android-data"),
    )
    ap.add_argument(
        "--platform-tools", type=Path, default=REPO.parent / "tools/platform-tools"
    )
    ap.add_argument("--backup", type=Path, default=REPO / "backups/first")
    ap.add_argument("--manifest", type=Path, default=REPO / "out/package/manifest.json")
    ap.add_argument("--experimental", action="store_true")
    ap.add_argument("--erase-data", action="store_true")
    args = ap.parse_args()
    suffix = ".exe" if (args.platform_tools / "adb.exe").exists() else ""
    adb, fb = (args.platform_tools / (n + suffix) for n in ("adb", "fastboot"))
    if args.action == "status":
        print(run(adb, "devices", "-l"))
        print(run(fb, "devices"))
        return
    tool = adb if args.action == "backup" else fb
    devices = run(tool, "devices")
    mode = "device" if args.action == "backup" else "fastboot"
    serials = [
        line.split()[0]
        for line in devices.splitlines()
        if len(line.split()) >= 2 and line.split()[1] == mode
    ]
    if len(serials) != 1:
        raise RuntimeError("exactly one authorized device required in the correct mode")
    serial = serials[0]
    if args.action == "backup":
        if (
            run(adb, "-s", serial, "shell", "getprop ro.product.device").strip()
            != "joyeuse"
        ):
            raise RuntimeError("recovery must identify joyeuse")
        if run(adb, "-s", serial, "shell", "id -u").strip() != "0":
            raise RuntimeError("root recovery required for verified partition backups")
        args.backup.mkdir(parents=True, exist_ok=False)
        records = {}
        for name in PARTITIONS:
            source = "/dev/block/by-name/" + name
            try:
                expected = int(
                    run(adb, "-s", serial, "shell", f"blockdev --getsize64 {source}")
                )
            except (RuntimeError, ValueError):
                if name in ("persist", "boot", "dtbo", "vbmeta"):
                    raise
                continue
            if expected <= 0:
                raise ValueError("invalid partition size")
            target = args.backup / (name + ".img")
            with target.open("xb") as out:
                result = subprocess.run(
                    [str(adb), "-s", serial, "exec-out", f"dd if={source} 2>/dev/null"],
                    stdout=out,
                    stderr=subprocess.PIPE,
                    timeout=600,
                    check=False,
                )
            if result.returncode or target.stat().st_size != expected:
                raise RuntimeError("backup incomplete: " + name)
            records[name] = {
                "file": target.name,
                "size": expected,
                "sha256": sha(target),
            }
        (args.backup / "manifest.json").write_text(
            json.dumps(
                {"serial": serial, "product": "joyeuse", "partitions": records},
                indent=2,
            )
        )
        print("Verified backup completed")
        return
    product = run(fb, "-s", serial, "getvar", "product")
    if not re.search(r"product:\s*joyeuse(?:\s|$)", product):
        raise RuntimeError("wrong product: " + product)
    unlocked = run(fb, "-s", serial, "oem", "device-info")
    if not re.search(r"Device unlocked:\s*true", unlocked, re.IGNORECASE):
        raise RuntimeError("bootloader is locked")
    if args.action == "restore-android-data":
        if not args.erase_data:
            raise RuntimeError("--erase-data required; formats userdata/cache")
        subprocess.run([str(fb), "-s", serial, "-w"], check=True)
        print(
            "Android data formatted; stock boot partitions preserved. Reboot manually."
        )
        return
    if not args.experimental:
        raise RuntimeError("--experimental required: tactile unverified on hardware")
    files = manifest_images(args.manifest)
    if args.action == "flash-root":
        if not args.erase_data:
            raise RuntimeError("--erase-data required")
        backup = json.loads((args.backup / "manifest.json").read_text())
        if backup.get("serial") != serial or backup.get("product") != "joyeuse":
            raise RuntimeError("backup belongs to another device")
        for name in ("persist", "boot", "dtbo", "vbmeta"):
            verify_file(args.backup, backup["partitions"][name])
        subprocess.run(
            [
                str(fb),
                "-s",
                serial,
                "-S",
                "512M",
                "flash",
                "userdata",
                str(files["root"]),
            ],
            check=True,
        )
        print("Root flashed. Re-enter fastboot if needed, then run boot separately.")
    else:
        subprocess.run([str(fb), "-s", serial, "boot", str(files["boot"])], check=True)


if __name__ == "__main__":
    main()
