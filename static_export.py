"""Generate a read-only, public GitHub Pages dashboard, with no API tokens."""
from __future__ import annotations
import json
from pathlib import Path
import dashboard

DEST = Path('docs')
DEST.mkdir(exist_ok=True)
(DEST / '.nojekyll').touch()
new_data = dashboard.data()
old_file = DEST / 'data.json'
if new_data.get('status') == 'FINISHED' and old_file.exists():
    old = json.loads(old_file.read_text(encoding='utf-8'))
    if old.get('status') == 'FINISHED':
        print('Final scoreboard already published; leaving it unchanged')
        raise SystemExit(0)
html = (Path(__file__).resolve().parent / 'templates/index.html').read_text(encoding='utf-8')
html = html.replace("fetch('/api/state'", "fetch('./data.json'")
(DEST / 'index.html').write_text(html, encoding='utf-8')
(DEST / 'data.json').write_text(json.dumps(new_data, ensure_ascii=True,
                                         separators=(',', ':'), indent=2), encoding='utf-8')
if new_data.get('status') == 'FINISHED':
    import shutil
    source = Path('results')
    dest = DEST / 'results'
    if source.exists():
        dest.mkdir(exist_ok=True)
        for csv in source.glob('*.csv'):
            shutil.copy2(csv, dest / csv.name)
print('Exported public static paper-only dashboard in docs/')
