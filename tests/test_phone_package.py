import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
def module(name,file):
    spec=importlib.util.spec_from_file_location(name,ROOT/'tools'/file)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
phone=module('phone','phone.py');sparse=module('sparse','raw-to-sparse.py')

class Package(unittest.TestCase):
    def test_sparse_roundtrip(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory);raw=bytes(1024*1024)+b'X'*4096
            (p/'raw').write_bytes(raw);report=sparse.convert(p/'raw',p/'sparse')
            with (p/'sparse').open('rb') as f:
                head=struct.unpack('<I4H4I',f.read(28));result=bytearray()
                for _ in range(head[7]):
                    kind,_,blocks,total=struct.unpack('<2H2I',f.read(12))
                    self.assertIn(kind,(0xcac1,0xcac2))
                    result.extend(f.read(4)*(blocks*1024) if kind==0xcac2 else f.read(total-12))
            self.assertEqual(bytes(result),raw)
            self.assertEqual(report['expanded_sha256'],hashlib.sha256(raw).hexdigest())

    def test_package_rejects_wrong_device_corruption_and_traversal(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)
            (p/'boot').write_bytes(b'ANDROID!'+bytes(4096))
            (p/'root').write_bytes(b'\x3a\xff\x26\xed'+bytes(4096))
            doc={'ready':True,'product':'joyeuse'}
            for name in ('boot','root'):
                file=p/name;doc[name]={'file':name,'size':file.stat().st_size,'sha256':phone.sha(file)}
            manifest=p/'manifest.json';manifest.write_text(json.dumps(doc))
            self.assertEqual(set(phone.manifest_images(manifest)),{'boot','root'})
            doc['product']='sweet';manifest.write_text(json.dumps(doc))
            with self.assertRaises(ValueError):phone.manifest_images(manifest)
            doc['product']='joyeuse';doc['boot']['file']='../outside'
            manifest.write_text(json.dumps(doc))
            with self.assertRaises(ValueError):phone.manifest_images(manifest)
            doc['boot']['file']='boot';manifest.write_text(json.dumps(doc));(p/'boot').write_bytes(b'changed')
            with self.assertRaises(ValueError):phone.manifest_images(manifest)

if __name__=='__main__':unittest.main()
