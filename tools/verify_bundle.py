"""Check a downloaded Git LFS checkout against its SHA-256 resource manifest."""
import hashlib
import json
from pathlib import Path


def main():
    base = Path(__file__).resolve().parents[1]
    manifest = json.loads((base / 'docs' / 'resource_manifest.json').read_text(encoding='utf-8'))
    failures = []
    for entry in manifest['files']:
        path = base / entry['path']
        if not path.is_file():
            failures.append(f"Missing: {entry['path']}")
            continue
        digest = hashlib.sha256()
        with path.open('rb') as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b''):
                digest.update(chunk)
        if path.stat().st_size != entry['bytes'] or digest.hexdigest() != entry['sha256']:
            failures.append(f"Wrong content (try git lfs pull): {entry['path']}")
    for message in failures:
        print(message)
    print(f"Checked {len(manifest['files'])} bundled resources; {len(failures)} failures")
    raise SystemExit(bool(failures))


if __name__ == '__main__':
    main()
