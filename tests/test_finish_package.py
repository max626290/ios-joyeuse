"""Exercise encrypted delivery through extraction and expanded-image validation."""

import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OPENSSL = shutil.which("openssl") or "C:/Program Files/Git/usr/bin/openssl.exe"
spec = importlib.util.spec_from_file_location("sparse", ROOT / "tools/raw-to-sparse.py")
sparse = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sparse)


@unittest.skipUnless(Path(OPENSSL).is_file(), "OpenSSL unavailable")
class FinishPackage(unittest.TestCase):
    def test_encrypted_roundtrip_and_expanded_hash_rejection(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory)
            src = p / "source"
            src.mkdir()
            key = p / "key"
            key.write_text("synthetic-test-key")
            (p / "raw").write_bytes(bytes(1024 * 1024) + b"A" * 4096)
            report = sparse.convert(p / "raw", src / "ios16-root.simg")
            (src / "shim-boot.img").write_bytes(b"ANDROID!" + bytes(64))
            manifest = {"ready": True, "product": "joyeuse"}
            for label, name in [("boot", "shim-boot.img"), ("root", "ios16-root.simg")]:
                data = (src / name).read_bytes()
                manifest[label] = {
                    "file": name,
                    "size": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(),
                }
            (src / "manifest.json").write_text(json.dumps(manifest))
            for valid in (True, False):
                if not valid:
                    report["expanded_sha256"] = "0" * 64
                (src / "root-expanded.json").write_text(json.dumps(report))
                archive = p / "package.tar.gz"
                with tarfile.open(archive, "w:gz") as tar:
                    for file in src.iterdir():
                        tar.add(file, arcname=file.name)
                subprocess.run(
                    [
                        OPENSSL,
                        "enc",
                        "-aes-256-cbc",
                        "-pbkdf2",
                        "-iter",
                        "200000",
                        "-salt",
                        "-in",
                        str(archive),
                        "-out",
                        str(p / "package.tar.gz.enc"),
                        "-pass",
                        "file:" + str(key),
                    ],
                    check=True,
                    capture_output=True,
                )
                result = subprocess.run(
                    [
                        sys.executable,
                        str(ROOT / "tools/finish-package.py"),
                        str(p),
                        "--key",
                        str(key),
                        "--out",
                        str(p / str(valid)),
                        "--openssl",
                        OPENSSL,
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if valid:
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(
                        (p / "True/ios16-root.simg").read_bytes(),
                        (src / "ios16-root.simg").read_bytes(),
                    )
                else:
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("expanded image hash mismatch", result.stderr)


if __name__ == "__main__":
    unittest.main()
