"""Convert a raw image into Android sparse chunks; preserve exact expanded bytes."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

def convert(source, target):
    size = source.stat().st_size
    if not size or size % 4096: raise ValueError('raw size must be a multiple of 4096')
    digest = hashlib.sha256(); count = 0
    with source.open('rb') as src, target.open('xb') as dst:
        dst.write(bytes(28))
        while data := src.read(1024*1024):
            digest.update(data); count += 1
            if not any(data):
                # FILL explicitly writes zeroes; DONT_CARE can retain old data.
                dst.write(struct.pack('<HHII',0xcac2,0,len(data)//4096,16))
                dst.write(bytes(4))
            else:
                dst.write(struct.pack('<HHII',0xcac1,0,len(data)//4096,len(data)+12))
                dst.write(data)
        dst.seek(0)
        dst.write(struct.pack('<I4H4I',0xed26ff3a,1,0,28,12,4096,size//4096,count,0))
    return {'expanded_size':size,'expanded_sha256':digest.hexdigest()}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('target',type=Path)
    a=p.parse_args();print(json.dumps(convert(a.source,a.target)))
