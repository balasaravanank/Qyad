"""Run from server/: python -m scripts.backup. SQLite only. No secrets printed."""
import os
from pathlib import Path
from datetime import datetime, timezone
import sqlite3
from sqlalchemy.engine import make_url
from app.db import DATABASE_URL
url=make_url(DATABASE_URL)
if url.drivername!='sqlite' or not url.database:raise SystemExit('SQLite file backup only')
source=Path(url.database)
if not source.is_file():raise SystemExit('Database does not exist')
dest=Path(os.getenv('BACKUP_DIR','backups'));dest.mkdir(mode=0o700,exist_ok=True)
target=dest/('qyad-'+datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')+'.db')
with sqlite3.connect(str(source)) as src, sqlite3.connect(str(target)) as dst:
    src.backup(dst)
    if dst.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise SystemExit('Backup integrity failed')
target.chmod(0o600)
for old in sorted(dest.glob('qyad-*.db'),reverse=True)[7:]:old.unlink()
print('Backup created and checked:',target)
print('Keep an encrypted off-server copy. Local retention: newest 7 files.')
