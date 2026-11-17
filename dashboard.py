"""Read-only local tournament scoreboard. No trade or admin endpoints."""
from __future__ import annotations
import json
import os
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

ROOT = Path(__file__).resolve().parent
DB = Path(os.getenv("DB_PATH", str(ROOT / "tournament.sqlite3")))
AGENTS = ("gemini_free", "groq_gptoss", "groq_qwen", "momentum_baseline")
app = FastAPI(title="Memecoin Arena | Read-only dashboard", docs_url=None, redoc_url=None)


def rows(conn, sql, args=()):
    return [dict(x) for x in conn.execute(sql, args).fetchall()]


def data():
    if not DB.exists():
        return {"status": "NOT_STARTED", "meta": {}, "scoreboard": [], "trades": [],
                "decisions": [], "research": [], "history": {}, "message": "No tournament database yet"}
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=3)
    conn.row_factory = sqlite3.Row
    try:
        meta = {x["key"]: json.loads(x["value"]) for x in
                conn.execute("SELECT key,value FROM meta")}
        snapshots = rows(conn, """SELECT * FROM snapshots WHERE rowid IN
                    (SELECT MAX(rowid) FROM snapshots GROUP BY agent)""")
        snapmap = {x["agent"]: x for x in snapshots}
        start_fx = float(meta.get("start_fx_cad_per_usd", 1.0))
        cash0 = 1000.0 / start_fx if start_fx else 1000.0
        scoreboard = []
        for agent in AGENTS:
            s = snapmap.get(agent, {})
            nav = float(s["equity_cad"]) if s.get("equity_cad") is not None else 1000.0
            name = {"gemini_free": "Gemini Flash (Free)", "groq_gptoss": "GPT-OSS 120B (Groq Free)",
                    "groq_qwen": "Qwen 3.8 27B (Groq Free)", "momentum_baseline": "Momentum Control"}[agent]
            h = rows(conn, "SELECT symbol,mint,quantity_raw,decimals,cost_usd "
                      "FROM holdings WHERE agent=?", (agent,))
            latest = conn.execute(
                "SELECT action, accepted, explanation, at_utc FROM decisions "
                "WHERE agent=? ORDER BY rowid DESC LIMIT 1", (agent,)).fetchone()
            if latest is None:
                decision_label, decision_health, decision_at = "PENDING", "PENDING", None
            else:
                decision_label = str(latest["action"] or "HOLD").upper()
                decision_at = latest["at_utc"]
                if latest["accepted"]:
                    decision_health = "OK"
                elif "Client Error" in (latest["explanation"] or "") or \
                     "API failure" in (latest["explanation"] or "") or \
                     "Read timed out" in (latest["explanation"] or ""):
                    decision_health = "API_ERROR"
                else:
                    decision_health = "REJECTED"
            scoreboard.append({"agent": agent, "name": name,
                               "last_decision": decision_label,
                               "last_decision_health": decision_health,
                               "last_decision_at": decision_at,
                               "nav_cad": round(nav, 2), "pnl_cad": round(nav-1000, 2),
                               "return_pct": round((nav/1000-1)*100, 2),
                               "cash_usd": round(float(s["cash_usd"]) if s.get("cash_usd") is not None else cash0, 2),
                               "exposure_pct": round(float(s.get("exposure_percent") or 0), 2),
                               "unsellable": int(s.get("untradeable_positions") or 0),
                               "holdings": h})
        scoreboard.sort(key=lambda x: x["nav_cad"], reverse=True)
        raw = rows(conn, "SELECT at_utc,agent,equity_cad FROM snapshots ORDER BY rowid DESC LIMIT 1600")
        history = {name: [] for name in AGENTS}
        for x in reversed(raw):
            if len(history[x["agent"]]) < 400:
                history[x["agent"]].append({"at": x["at_utc"], "equity": round(x["equity_cad"], 2)})
        total_trades = conn.execute("SELECT COUNT(*) FROM trades").fetchone()[0]
        trades = rows(conn, "SELECT at_utc,agent,side,mint,symbol,usd_amount,note "
                      "FROM trades ORDER BY rowid DESC LIMIT 65")
        decisions = rows(conn, "SELECT at_utc,agent,action,mint,reason,accepted,explanation "
                         "FROM decisions ORDER BY rowid DESC LIMIT 65")
        research = rows(conn, "SELECT at_utc,mint,symbol,name,organic_score,liquidity_usd,"
                        "price_usd,momentum_5m,audit_json FROM research_snapshots "
                        "WHERE at_utc=(SELECT MAX(at_utc) FROM research_snapshots) "
                        "ORDER BY organic_score DESC LIMIT 25")
        for r in research:
            r["audit"] = json.loads(r.pop("audit_json") or "{}")
        if meta.get("finished"):
            status = "FINISHED"
        elif not meta.get("started_at"):
            status = "NOT_STARTED"
        else:
            last = meta.get("last_healthy_tick")
            try:
                heartbeat_age = time.time() - datetime.fromisoformat(last).timestamp()
            except (TypeError, ValueError):
                heartbeat_age = float("inf")
            status = "LIVE" if heartbeat_age < max(12*60, 4*int(os.getenv("INTERVAL_SECONDS", "120"))) else "STALE"
        return {"status": status, "meta": meta, "scoreboard": scoreboard, "trades": trades,
                "decisions": decisions, "research": research, "history": history,
                "total_trades": total_trades,
                "asof_utc": datetime.now(timezone.utc).isoformat(),
                "next_required": [] if meta.get("started_at") else
                    ["Connect model API keys", "Validate market data", "Start the worker"]}
    finally:
        conn.close()


@app.get("/", response_class=HTMLResponse)
def index():
    return (ROOT / "templates" / "index.html").read_text(encoding="utf-8")


@app.get("/api/state")
def state():
    try:
        return data()
    except (sqlite3.Error, OSError) as exc:
        return {"status": "ERROR", "message": f"Database unavailable: {type(exc).__name__}"}


@app.get("/health")
def health():
    d = data()
    return {"status": d["status"], "worker_online": d["status"] == "LIVE"}
