#!/bin/bash
set -euo pipefail
repo=$(cd "$(dirname "$0")/.." && pwd)
cd "$repo"
mkdir -p out/package ipsw fw
openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 -in build-inputs.enc -out out/inputs.zip -pass env:ROOT_TRANSFER_PASSWORD
unzip -q out/inputs.zip -d fw
rm out/inputs.zip
url='https://updates.cdn-apple.com/2025FallFCS/fullrestores/122-77006/1158E502-D76D-4226-AA06-ED5E30CD1111/iPhone10,3,iPhone10,6_16.7.16_20H392_Restore.ipsw'
for item in 087-86698-044.dmg 087-86593-047.dmg 087-86715-047.dmg DeviceTree.d22ap.im4p; do
    python3 tools/remotezip.py "$url" "$item" ipsw
done
ipsw img4 im4p extract ipsw/Firmware/all_flash/DeviceTree.d22ap.im4p -o fw/d22ap.adt
gh run download 43405019892 -R "$GITHUB_REPOSITORY" -n joyeuse-xnu -D out/kernel
python3 tools/mkadt.py out/joyeuse.adt --device joyeuse --highmem --product fw/d22ap.adt \
    --touch-controller novatek --touch-firmware fw/novatek_ts_tianma_fw.bin \
    --novatek-spi-pins 55 53 54 56 --wifi-mac fw/wifi-mac.bin --bluetooth-mac fw/bluetooth-mac.bin
tools/cmdline.sh good > out/cmdline.txt
python3 tools/mkpayload.py out/kernel/kernel.development.sweet out/joyeuse.adt out/payload.bin --cmdline-file out/cmdline.txt
export PATH="$(brew --prefix llvm)/bin:$PATH"
python3 tools/build-shim.py fw/dtb out/payload.bin out/package/shim-boot.img
tools/mkiosroot-macos.sh ipsw/087-86698-044.dmg ipsw/087-86593-047.dmg ipsw/087-86715-047.dmg out/ios16-root.img 16G
python3 tools/raw-to-sparse.py out/ios16-root.img out/package/ios16-root.simg > out/package/root-expanded.json
rm out/ios16-root.img
python3 - <<'PY'
import hashlib,json
from pathlib import Path
p=Path('out/package')
def record(name):
    f=p/name
    with f.open('rb') as stream: digest=hashlib.file_digest(stream,'sha256').hexdigest()
    return {'file':name,'size':f.stat().st_size,'sha256':digest}
m={'ready':True,'product':'joyeuse','ios':'16.7.16','build':'20H392',
   'driver':'NT36675 experimental','hardware_validated':False,
   'kernel_source':'211c917','kernel_run':43405019892,'spi_pins':[55,53,54,56],
   'network_identity':'synthetic locally administered MACs; radios unvalidated',
   'boot':record('shim-boot.img'),'root':record('ios16-root.simg')}
(p/'manifest.json').write_text(json.dumps(m,indent=2))
PY
tar -C out/package -czf - . | openssl enc -aes-256-cbc -pbkdf2 -iter 200000 -salt \
    -pass env:ROOT_TRANSFER_PASSWORD -out out/package.tar.gz.enc
