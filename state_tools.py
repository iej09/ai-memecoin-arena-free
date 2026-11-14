"""Persist the public paper-only SQLite ledger between ephemeral GitHub Action jobs.

No secrets are put in this file or in the generated website. To preserve a clean
snapshot, use SQLite's online backup API then gzip the snapshot to a tracked file.
"""
from __future__ import annotations
import argparse
import gzip
import os
import shutil
import sqlite3
from pathlib import Path

DB = Path(os.getenv('DB_PATH', 'state/tournament.sqlite3'))
BACKUP = Path('state/tournament.sqlite3.gz')


def restore():
    DB.parent.mkdir(parents=True, exist_ok=True)
    if not BACKUP.is_file():
        print('No saved state; this is a fresh tournament')
        return
    with gzip.open(BACKUP, 'rb') as src, DB.open('wb') as dest:
        shutil.copyfileobj(src, dest)
    with sqlite3.connect(DB) as conn:
        result = conn.execute('PRAGMA integrity_check').fetchone()[0]
        if result != 'ok':
            raise RuntimeError('Persisted SQLite database is corrupt: ' + result)
    print('Restored the original tournament ledger, including its deadline')


def save():
    if not DB.exists():
        print('No tournament DB created. Nothing to save')
        return
    BACKUP.parent.mkdir(parents=True, exist_ok=True)
    tmp = DB.with_suffix('.backup-tmp')
    try:
        with sqlite3.connect(DB) as source, sqlite3.connect(tmp) as target:
            source.backup(target)
        with tmp.open('rb') as src, BACKUP.open('wb') as out:
            with gzip.GzipFile(fileobj=out, mode='wb', filename='', mtime=0, compresslevel=9) as dst:
                shutil.copyfileobj(src, dst)
    finally:
        tmp.unlink(missing_ok=True)
    print('Committed a consistent compressed database for the next scheduled tick')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['restore', 'save'])
    args = parser.parse_args()
    if args.action == 'restore':
        restore()
    else:
        save()
