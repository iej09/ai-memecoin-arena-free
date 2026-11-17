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
# Repository-native fallback scoreboard, available even before Pages is enabled.
md = ["# AI Memecoin Arena — read-only status", "",
      "This is a **paper-only** simulation; no real crypto orders are sent.", "",
      f"**Status:** {new_data.get('status', 'UNKNOWN')}",
      f"**As of (UTC):** {new_data.get('asof_utc', 'not run')}", "",
      "| Competitor | Virtual CAD | Return | Exposure | Last decision |",
      "|---|---:|---:|---:|---|"]
for account in new_data.get('scoreboard', []):
    health = account.get("last_decision_health", "PENDING")
    action = account.get("last_decision", "PENDING")
    label = "API ERROR" if health == "API_ERROR" else ("REJECTED" if health == "REJECTED" else action)
    md.append(f"| {account['name']} | ${account['nav_cad']:,.2f} | "
              f"{account['return_pct']:+.2f}% | {account['exposure_pct']:.1f}% | {label} |")
if not new_data.get('scoreboard'):
    md.append("| No portfolios yet | — | — | — | — |")
meta = new_data.get('meta') or {}
md.extend(["", f"**Market status:** {meta.get('last_market_status', 'not checked')}",
           f"**Last healthy scan:** {meta.get('last_healthy_tick', 'none')}",
           "", "GitHub Actions and data-provider outages may delay this snapshot."])
if any(a.get("last_decision_health") == "API_ERROR" for a in new_data.get("scoreboard", [])):
    md.extend(["", "**AI warning:** A provider call failed at the last decision. This is not a genuine HOLD. Review [detailed data](docs/data.json)."])
Path('STATUS.md').write_text("\n".join(md) + "\n", encoding='utf-8')

print('Exported public static paper-only dashboard in docs/')
