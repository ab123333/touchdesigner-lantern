"""Refresh checksums after intentionally saving a new distributable TD project."""
import hashlib
import json
from pathlib import Path


def main():
    base = Path(__file__).resolve().parents[1]
    files = [base / 'Lantern.toe'] + sorted((base / 'assets').rglob('*'))
    entries = []
    for path in files:
        if not path.is_file():
            continue
        digest = hashlib.sha256()
        with path.open('rb') as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b''):
                digest.update(chunk)
        entries.append({'path': path.relative_to(base).as_posix(), 'bytes': path.stat().st_size,
                        'sha256': digest.hexdigest()})
    manifest = {'touchdesigner_build': '2023.11600', 'files': entries,
                'embedded_resources': 'embedded_resources.json',
                'standard_resources': 'TD installation supplies standard camera/null display geometry'}
    (base / 'docs' / 'resource_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(f'Manifest contains {len(entries)} files')


if __name__ == '__main__':
    main()
