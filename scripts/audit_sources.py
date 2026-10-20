"""Resolve cited DOI metadata for failed models; never infer equation fidelity.

Network evidence is cached outside the repository. A resolved citation does not
prove that a model was extracted from it. This script never edits definitions.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit
import urllib.request
import urllib.error
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--audit', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--cache', required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    cache = Path(args.cache); cache.mkdir(parents=True, exist_ok=True)
    audit_bytes = Path(args.audit).read_bytes()
    audit = json.loads(audit_bytes)
    entries = []
    for run in audit['models']:
        if run['status'] != 'failed': continue
        path = root / run['file']; raw = path.read_bytes()
        model = json.loads(raw)
        parsed = urlsplit(model.get('source') or '')
        doi = unquote(parsed.path.lstrip('/')) if parsed.hostname in {'doi.org', 'dx.doi.org'} else None
        current_hash = hashlib.sha256(raw).hexdigest()
        entries.append({'file': run['file'], 'id': model['id'], 'sha256': current_hash,
            'historical_audit_sha256': run.get('sha256'),
            'changed_since_numerical_audit': current_hash != run.get('sha256'),
            'source': model.get('source'), 'reference': model.get('reference'), 'doi': doi,
            'historical_default_error': run.get('error'), 'source_fidelity': 'not established'})
    def resolve(doi):
        filename = cache / (hashlib.sha256(doi.encode()).hexdigest() + '.json')
        url = 'https://api.crossref.org/works/' + quote(doi, safe='')
        try:
            if not filename.exists():
                time.sleep(1)
                request = urllib.request.Request(url, headers={'User-Agent': 'StockAndFlow-SourceAudit/1.4'})
                try:
                    with urllib.request.urlopen(request, timeout=25) as response: raw = response.read()
                except urllib.error.HTTPError as exc:
                    if exc.code != 429: raise
                    time.sleep(min(30, max(10, int(exc.headers.get('Retry-After', '10')))))
                    with urllib.request.urlopen(request, timeout=25) as response: raw = response.read()
                json.loads(raw); filename.write_bytes(raw)
            raw = filename.read_bytes(); message = json.loads(raw)['message']
            return doi, {'status': 'metadata_resolved', 'metadata_url': url,
                'response_sha256': hashlib.sha256(raw).hexdigest(), 'title': message.get('title'),
                'authors': [a.get('family') for a in message.get('author', [])],
                'container': message.get('container-title'), 'published': message.get('published'),
                'publisher': message.get('publisher'), 'type': message.get('type')}
        except Exception as exc:
            return doi, {'status': 'retrieval_failed', 'metadata_url': url, 'error': str(exc)}
    with ThreadPoolExecutor(max_workers=1) as pool:
        metadata = dict(pool.map(resolve, sorted({e['doi'] for e in entries if e['doi']})))
    for entry in entries:
        entry['citation_check'] = metadata.get(entry['doi'], {'status': 'non_doi_source_requires_manual_review'})
    report = {'checked_at': datetime.now(timezone.utc).isoformat(), 'scope': 'All failed tracked defaults in supplied audit',
        'input_audit': {'file': Path(args.audit).name,
                        'sha256': hashlib.sha256(audit_bytes).hexdigest(),
                        'error_scope': 'Historical results only; this source audit does not rerun simulations'},
        'meaning': 'Publisher-deposited DOI metadata only; not a verification of equations, parameters, units or calibration.',
        'counts': {'models': len(entries), 'unique_dois': len(metadata),
                   'resolved_dois': sum(m['status'] == 'metadata_resolved' for m in metadata.values())}, 'models': entries}
    Path(args.output).write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report['counts']))

if __name__ == '__main__': main()
