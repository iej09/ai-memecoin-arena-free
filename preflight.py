"""Re-check free AI credentials only when needed, without starting the clock."""
from __future__ import annotations
import os
import subprocess
import sys
import time
from tournament import Ledger, DB_PATH, MODELS

ledger = Ledger(DB_PATH)
if ledger.meta('started_at'):
    print('Tournament already started; preserving the original deadline')
    raise SystemExit(0)
checked = float(ledger.meta('preflight_passed_at', 0))
models = {k: os.getenv(v[1]) or v[2] for k, v in MODELS.items()}
if checked and time.time() - checked < 86400 and ledger.meta('preflight_models') == models:
    print('Recent FREE-tier provider checks are still valid')
    raise SystemExit(0)
ledger.db.close()
print('Running FREE-tier AI and market preflight; this does not start a contest')
subprocess.run([sys.executable, 'tournament.py', '--check'], check=True)
