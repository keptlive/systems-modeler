"""Verify current bytes before recovering a hash-bound historical model version.

Historical preservation claims stay tested against their original release. New
repair tests separately exercise current equations and intentional changes.
"""
import hashlib
import json

def v17_bytes(root,relative):
    raw=(root/relative).read_bytes()
    chain=json.loads((root/'operations/model-revision-chain-v18.json').read_text())
    row=next((r for r in chain['models'] if r['file']==str(relative)),None)
    if row is None:return raw
    assert hashlib.sha256(raw).hexdigest()==row['after_sha256'],str(relative)
    previous=row['before_text'].encode()
    assert hashlib.sha256(previous).hexdigest()==row['before_sha256'],str(relative)
    return previous
