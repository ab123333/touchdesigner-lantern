"""ZIP tracked working-tree files with resolved LFS assets, never LFS pointers."""
import subprocess
import zipfile
from pathlib import Path


def main():
    base = Path(__file__).resolve().parents[1]
    tracked = subprocess.check_output(['git', 'ls-files', '-z'], cwd=base).decode('utf-8').split('\0')
    paths = [base / name for name in tracked if name]
    for path in paths:
        with path.open('rb') as handle:
            if handle.read(80).startswith(b'version https://git-lfs.github.com/spec/v1'):
                raise RuntimeError(f'Unresolved LFS asset: {path.name}; run git lfs pull')
    output = base / 'dist' / 'Lantern-v0.1.0-full.zip'
    output.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in paths:
            archive.write(path, 'touchdesigner-lantern/' + path.relative_to(base).as_posix())
    with zipfile.ZipFile(output) as archive:
        bad = archive.testzip()
        if bad:
            raise RuntimeError(f'Archive CRC error: {bad}')
    print(f'{output}: {len(paths)} files, {output.stat().st_size} bytes, CRC OK')


if __name__ == '__main__':
    main()
