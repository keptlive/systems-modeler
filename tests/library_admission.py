"""Exclude only exact, individually approved admissions from baseline duplicate checks."""
import hashlib,json

def baseline_models(root, excluded_ids=None):
    quality_path=root/'operations/library-quality-20261024.json'
    if quality_path.exists():
        quality=json.loads(quality_path.read_text())
        for row in quality['retired']+quality['replaced']:
            assert hashlib.sha256((root/row['archive']).read_bytes()).hexdigest()==row['before_sha256']
            assert row['before_sha256'] in (root/row['review']).read_text()
        for row in quality['retired']:assert not (root/row['file']).exists()
        for row in quality['replaced']:
            assert (root/row['file']).read_bytes()==(root/row['source']).read_bytes()
            assert hashlib.sha256((root/row['file']).read_bytes()).hexdigest()==row['after_sha256']
            assert row['after_sha256'] in (root/row['review']).read_text()
    manifest=root/'operations/library-admissions-20261024.json'
    admitted=json.loads(manifest.read_text())['models'] if manifest.exists() else []
    allowed={row['file']:row for row in admitted}
    output=[]
    seen=set()
    for path in (root/'models').rglob('*.json'):
        relative=str(path.relative_to(root));raw=json.loads(path.read_text())
        assert raw['id'] not in seen,raw['id']
        seen.add(raw['id'])
        if relative in allowed:
            row=allowed[relative]
            assert raw['id']==row['id']
            assert hashlib.sha256(path.read_bytes()).hexdigest()==row['sha256']
            assert path.read_bytes()==(root/row['source']).read_bytes()
            assert row['sha256'] in (root/row['review']).read_text()
            if excluded_ids is not None and raw['id'] not in excluded_ids:
                output.append(raw)
        else:output.append(raw)
    assert all((root/name).exists() for name in allowed)
    return output
