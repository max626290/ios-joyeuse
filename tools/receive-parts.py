"""Download and acknowledge encrypted parts; only delete artifacts after local ZIP extraction."""

import argparse
import hashlib
import json
import subprocess
import time
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument("--gh", required=True)
p.add_argument("--run", required=True)
p.add_argument("--repo", default="max626290/ios-joyeuse")
p.add_argument("--out", type=Path, required=True)
a = p.parse_args()
a.out.mkdir(parents=True, exist_ok=True)


def gh(*args):
    return subprocess.check_output([a.gh, *args], text=True)


done = set()
deadline = time.monotonic() + 4 * 3600
while time.monotonic() < deadline:
    records = json.loads(
        gh("api", f"repos/{a.repo}/actions/runs/{a.run}/artifacts?per_page=100")
    )["artifacts"]
    for item in records:
        name = item["name"]
        if not name.startswith("ios-transfer-") or name in done:
            continue
        dest = a.out / name
        if not dest.exists():
            gh("run", "download", a.run, "-R", a.repo, "-n", name, "-D", str(dest))
        # Presence of the complete expected file is required before deletion.
        expected = dest / (
            "transfer-manifest.json" if name.endswith("complete") else name + ".bin"
        )
        if not expected.is_file() or not expected.stat().st_size:
            raise RuntimeError("incomplete download")
        gh(
            "api",
            "--method",
            "DELETE",
            f"repos/{a.repo}/actions/artifacts/{item['id']}",
        )
        done.add(name)
        print("Received", name, flush=True)
        if name == "ios-transfer-complete":
            manifest = json.loads(expected.read_text())
            total = 0
            target = a.out / "package.tar.gz.enc"
            with target.open("xb") as output:
                for entry in manifest["parts"]:
                    file = a.out / entry["name"] / entry["file"]
                    data = file.read_bytes()
                    if (
                        len(data) != entry["size"]
                        or hashlib.sha256(data).hexdigest() != entry["sha256"]
                    ):
                        raise RuntimeError("part verification failed")
                    output.write(data)
                    total += len(data)
            if total != manifest["size"]:
                raise RuntimeError("size mismatch")
            for entry in manifest["parts"]:
                (a.out / entry["name"] / entry["file"]).unlink()
            print("Transfer verified", target, flush=True)
            raise SystemExit(0)
    state = json.loads(
        gh("run", "view", a.run, "-R", a.repo, "--json", "status,conclusion")
    )
    if state["status"] == "completed" and state["conclusion"] != "success":
        raise RuntimeError(str(state))
    time.sleep(15)
raise TimeoutError("transfer timeout")
