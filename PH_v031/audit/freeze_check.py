from __future__ import annotations
import hashlib,json
from pathlib import Path

def verify(root,freeze):
    root=Path(root); bad=[]
    for rel,want in freeze['source_hashes'].items():
        got=hashlib.sha256((root/rel).read_bytes()).hexdigest()
        if got!=want: bad.append(rel)
    return bad
