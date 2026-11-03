#!/usr/bin/env python3
"""Build the installable Project Archiver 3.x zip.

The zip is written to dist/ (git-ignored) and attached to a GitHub release, not committed:

    python tools/build_dist.py
    git tag v3.1.0
    git push origin v3.1.0
    gh release create v3.1.0 --title v3.1.0 --notes-file notes.md dist/Project-Archiver-3.1.0.zip

The version comes from Project-Archiver/Project-Archiver.manifest, which is what Fusion shows.
The archive has a single top-level Project-Archiver folder, matching the layout Fusion expects:
the folder name must match the add-in name in the manifest.
"""

import argparse
import json
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ADDIN = REPO / 'Project-Archiver'
MANIFEST = ADDIN / 'Project-Archiver.manifest'
ADDIN_NAME = 'Project-Archiver'

# Directories that never belong in a distribution: Python caches, editor state, and the leftover
# apper submodule from the 2.x branch when this checkout has one.
EXCLUDED_DIRS = {'__pycache__', '.vscode', '.idea', 'apper'}

# Files that must be present in the finished archive.
REQUIRED_ENTRIES = (
    'Project-Archiver/Project-Archiver.py',
    'Project-Archiver/Project-Archiver.manifest',
    'Project-Archiver/config.py',
    'Project-Archiver/commands/__init__.py',
    'Project-Archiver/lib/archiverUtils/exporter.py',
    'Project-Archiver/lib/fusionAddInUtils/__init__.py',
)


def read_version():
    with MANIFEST.open(encoding='utf-8') as handle:
        return json.load(handle)['version']


def check_sources():
    for relative in ('Project-Archiver.py', 'config.py', 'commands/__init__.py'):
        if not (ADDIN / relative).is_file():
            raise SystemExit('error: missing {}/{}'.format(ADDIN_NAME, relative))


def iter_addin_files():
    for path in sorted(ADDIN.rglob('*')):
        if not path.is_file():
            continue
        if any(part in EXCLUDED_DIRS for part in path.relative_to(ADDIN).parts):
            continue
        if path.suffix in ('.pyc', '.pyo'):
            continue
        yield path


def write_zip(stage_root, zip_path):
    with zipfile.ZipFile(str(zip_path), 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in iter_addin_files():
            archive.write(str(path), path.relative_to(REPO).as_posix())


def verify(zip_path):
    with zipfile.ZipFile(str(zip_path)) as archive:
        names = archive.namelist()
        if archive.testzip() is not None:
            raise SystemExit('error: the created archive is corrupt')

    missing = [entry for entry in REQUIRED_ENTRIES if entry not in names]
    if missing:
        raise SystemExit('error: archive is missing: {}'.format(', '.join(missing)))

    return len(names)


def main():
    parser = argparse.ArgumentParser(description='Build the Project Archiver release zip.')
    parser.add_argument('--output', type=Path, default=None,
                        help='zip path (default: dist/Project-Archiver-<version>.zip)')
    args = parser.parse_args()

    version = read_version()
    check_sources()

    zip_path = args.output or (REPO / 'dist' / '{}-{}.zip'.format(ADDIN_NAME, version))
    zip_path = zip_path.resolve()
    zip_path.parent.mkdir(parents=True, exist_ok=True)

    if zip_path.exists():
        zip_path.unlink()

    entry_count = 0
    write_zip(None, zip_path)
    entry_count = verify(zip_path)

    print('built {} ({} files, {:,} bytes)'.format(zip_path, entry_count, zip_path.stat().st_size))
    print('attach it to a release, e.g.:')
    print('  gh release create v{} --title v{} --notes "..." "{}"'.format(version, version, zip_path))
    return 0


if __name__ == '__main__':
    sys.exit(main())
