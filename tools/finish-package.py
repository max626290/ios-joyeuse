"""Decrypt the received package directly to its final files (no extra multi-GB tar)."""

import argparse
import hashlib
import json
import struct
import subprocess
import tarfile
from pathlib import Path

from phone import manifest_images

p = argparse.ArgumentParser()
p.add_argument("transfer", type=Path)
p.add_argument("--openssl", default="C:/Program Files/Git/usr/bin/openssl.exe")
p.add_argument(
    "--out", type=Path, default=Path(__file__).resolve().parents[1] / "out/package"
)
p.add_argument(
    "--key", type=Path, default=Path(__file__).resolve().parents[1] / "fw/transfer.key"
)
a = p.parse_args()
a.out.mkdir(parents=True, exist_ok=True)
allowed = {"manifest.json", "shim-boot.img", "ios16-root.simg", "root-expanded.json"}
seen = set()
proc = subprocess.Popen(
    [
        a.openssl,
        "enc",
        "-d",
        "-aes-256-cbc",
        "-pbkdf2",
        "-iter",
        "200000",
        "-in",
        str(a.transfer / "package.tar.gz.enc"),
        "-pass",
        "file:" + str(a.key),
    ],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
)
try:
    with tarfile.open(fileobj=proc.stdout, mode="r|gz") as tar:
        for entry in tar:
            if entry.isdir() and entry.name in (".", "./"):
                continue
            name = entry.name.removeprefix("./")
            if not entry.isfile() or name not in allowed or name in seen:
                raise ValueError("unexpected package member")
            if entry.size > 20 * 1024**3:
                raise ValueError("member too large")
            final = a.out / name
            if final.exists():
                raise FileExistsError(final)
            temp = a.out / (name + ".partial")
            with tar.extractfile(entry) as src, temp.open("xb") as dst:
                while chunk := src.read(1024 * 1024):
                    dst.write(chunk)
            temp.rename(final)
            seen.add(name)
            print("Extracted", name, flush=True)
    # Drain OpenSSL output to avoid blocking its final write after tar EOF.
    while proc.stdout.read(1024 * 1024):
        pass
    if proc.wait() != 0:
        raise RuntimeError(proc.stderr.read().decode(errors="replace"))
except BaseException:
    proc.kill()
    proc.wait()
    raise
if seen != allowed:
    raise ValueError("missing package files")
files = manifest_images(a.out / "manifest.json")
expected = json.loads((a.out / "root-expanded.json").read_text())
digest = hashlib.sha256()
expanded = 0
with files["root"].open("rb") as f:
    magic, major, minor, hs, cs, bs, blocks, chunks, crc = struct.unpack(
        "<I4H4I", f.read(28)
    )
    if (magic, major, hs, cs, bs) != (0xED26FF3A, 1, 28, 12, 4096):
        raise ValueError("unsupported sparse format")
    for _ in range(chunks):
        kind, _, count, total = struct.unpack("<2H2I", f.read(12))
        left = count * bs
        expanded += left
        if kind not in (0xCAC1, 0xCAC2) or total != (
            12 + left if kind == 0xCAC1 else 16
        ):
            raise ValueError("bad sparse chunk")
        fill = f.read(4) if kind == 0xCAC2 else b""
        if kind == 0xCAC2 and len(fill) != 4:
            raise ValueError("truncated sparse fill")
        while left:
            n = min(left, 1024 * 1024)
            data = f.read(n) if kind == 0xCAC1 else fill * (n // 4)
            if len(data) != n:
                raise ValueError("truncated sparse image")
            digest.update(data)
            left -= n
    if f.read(1) or expanded != blocks * bs:
        raise ValueError("sparse size mismatch")
if (
    expanded != expected["expanded_size"]
    or digest.hexdigest() != expected["expanded_sha256"]
):
    raise ValueError("expanded image hash mismatch")
print(
    "Package hashes and expanded root image verified. Hardware touch remains untested.",
    flush=True,
)
