import math
import time
from pathlib import Path

import pytest

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tournament as arena
import dashboard
from research import valid_mint, deep_research


class FakeMarket:
    def __init__(self, sellable=True):
        self.sellable = sellable
        self.queries = []

    def quote(self, input_mint, output_mint, amount_raw):
        self.queries.append((input_mint, output_mint, amount_raw))
        if input_mint == arena.USDC and output_mint != arena.USDC:
            return amount_raw * 2  # fictional token price $0.50, six decimals
        if output_mint == arena.USDC and self.sellable:
            return amount_raw // 2
        return None


def token(mint):
    return {"id": mint, "symbol": "TEST", "name": "Test coin", "decimals": 6,
            "tokenProgram": arena.SPL_TOKEN_PROGRAM,
            "liquidity": 100_000, "organicScore": 65, "holderCount": 600,
            "audit": {"isSus": False, "mintAuthorityDisabled": True,
                      "freezeAuthorityDisabled": True, "topHoldersPercentage": 12},
            "stats5m": {"priceChange": 4, "numBuys": 300, "numSells": 150},
            "stats1h": {"priceChange": 12}}


@pytest.fixture
def running(tmp_path):
    ledger = arena.Ledger(tmp_path / "test.sqlite3")
    ledger.initialize(1.35)
    market = FakeMarket()
    engine = arena.Engine(ledger, market)
    engine.fx = 1.35
    return ledger, market, engine


def test_safe_eligibility_and_mint():
    assert valid_mint("JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN")
    assert not valid_mint("bad-token; DROP TABLE trades")
    t = token("A" * 32)
    assert arena.eligible(t)
    assert not arena.eligible({**t, "audit": {**t["audit"], "mintAuthorityDisabled": False}})
    assert not arena.eligible({**t, "audit": {**t["audit"], "isSus": True}})
    assert not arena.eligible({**t, "liquidity": 400})


def test_every_bot_starts_at_1000_cad(running):
    ledger, _, engine = running
    for agent in arena.AGENTS:
        p = engine.portfolio_packet(agent)
        assert math.isclose(p["cash_usd"] * 1.35, 1000, abs_tol=0.01)
        assert p["holdings"] == []


def test_buy_sell_paper_only_and_cash_never_negative(running):
    ledger, m, e = running
    t = token("A" * 32)
    ok, msg = e.execute("gemini_free", {"action": "BUY", "mint": t["id"], "usd_amount": 50}, {t["id"]: t})
    assert ok, msg
    h = ledger.portfolio("gemini_free")["holdings"]
    assert len(h) == 1 and h[0]["quantity_raw"] > 0
    assert ledger.portfolio("gemini_free")["cash_usd"] >= 0
    ok, msg = e.execute("gemini_free", {"action": "SELL", "mint": t["id"]}, {})
    assert ok, msg
    assert ledger.portfolio("gemini_free")["holdings"] == []
    assert ledger.portfolio("gemini_free")["cash_usd"] < 1000 / 1.35  # fees, drift
    assert len(m.queries) >= 3


def test_75_percent_portfolio_cap(running):
    ledger, _, engine = running
    mints = [chr(65+i) * 32 for i in range(5)]
    for mint in mints:
        t = token(mint)
        engine.execute("gemini_free", {"action": "BUY", "mint": mint, "usd_amount": 10000}, {mint: t})
        engine.risk_controls("gemini_free")
        assert engine.portfolio_packet("gemini_free")["exposure_percent"] <= 75.001
    assert ledger.portfolio("gemini_free")["cash_usd"] >= 0


def test_no_buy_without_reverse_sell_route(running):
    ledger, market, e = running
    market.sellable = False
    t = token("A" * 32)
    ok, why = e.execute("gemini_free", {"action": "BUY", "mint": t["id"], "usd_amount": 40}, {t["id"]: t})
    assert not ok and "reverse route" in why
    assert ledger.portfolio("gemini_free")["holdings"] == []


def test_reject_foreign_mint_and_post_deadline(running):
    ledger, _, e = running
    a = token("A" * 32)
    no, why = e.execute("gemini_free", {"action": "BUY", "mint": "B" * 32, "usd_amount": 30}, {a["id"]: a})
    assert not no
    ledger.set_meta("deadline", time.time() - 1)
    no, why = e.execute("gemini_free", {"action": "BUY", "mint": a["id"], "usd_amount": 30}, {a["id"]: a})
    assert not no and "deadline" in why


def test_failed_discovery_cannot_start_competition(tmp_path, monkeypatch):
    ledger = arena.Ledger(tmp_path / "no-start.sqlite3")
    class NoDataMarket(FakeMarket):
        def discover(self):
            raise RuntimeError("network offline")
    e = arena.Engine(ledger, NoDataMarket())
    monkeypatch.setattr(arena, "fx_cad_per_usd", lambda: 1.35)
    e.step()  # Publish a NOT_STARTED dashboard rather than failing the cloud workflow.
    assert ledger.meta("started_at") is None
    assert ledger.meta("last_market_status") == "MARKET_UNAVAILABLE"


def test_research_rejects_bad_mint_without_network():
    assert all(v["status"] in ("invalid_mint", "not_configured")
               for v in deep_research("<evil>")["sources"].values())


def test_dashboard_handles_empty_and_zero_value(tmp_path, monkeypatch):
    monkeypatch.setattr(dashboard, "DB", tmp_path / "nonexistent.sqlite3")
    assert dashboard.data()["status"] == "NOT_STARTED"
    ledger = arena.Ledger(tmp_path / "example.sqlite3")
    ledger.initialize(1.35)
    ledger.snapshot("gemini_free", 0, 0, 1.35, 1)
    monkeypatch.setattr(dashboard, "DB", tmp_path / "example.sqlite3")
    d = dashboard.data()
    assert next(x for x in d["scoreboard"] if x["agent"] == "gemini_free")["nav_cad"] == 0


def test_json_decisions_free_only(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_API_KEY", "should-never-be-used")
    calls = []
    sample = '{"action":"HOLD","mint":"","usd_amount":0,"research_type":"ALL","reason":"Testing"}'

    def fake_http(method, url, **kwargs):
        calls.append((url, kwargs["body"]))
        if "generativelanguage" in url:
            return {"candidates": [{"content": {"parts": [{"text": sample}]}}]}
        if "api.groq.com" in url:
            return {"choices": [{"message": {"content": sample}}]}
        raise AssertionError("Unexpected, potentially paid API: " + url)

    monkeypatch.setattr(arena, "http_json", fake_http)
    for model in ("gemini_free", "groq_gptoss", "groq_qwen"):
        assert arena.llm_decision(model, {"candidates": []})["action"] == "HOLD"
    assert "generateContent" in calls[0][0]
    assert calls[0][1]["generationConfig"]["responseMimeType"] == "application/json"
    assert calls[1][1]["response_format"]["type"] == "json_schema"
    assert calls[1][1]["response_format"]["json_schema"]["strict"] is True
    assert not any("api.openai.com" in url or "anthropic.com" in url for url, _ in calls)


def test_only_free_tier_credentials_are_required(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "fake-free")
    monkeypatch.setenv("GROQ_API_KEY", "fake-free")
    arena.validate_keys()


def test_live_packet_is_bounded_for_free_ai():
    packet = {"candidates": [{"id": "A" * 32, "name": "T", "irrelevant": "x" * 5000} for _ in range(80)],
              "portfolio": {"holdings": [], "cash_usd": 1000}}
    packed = arena.compact_free_packet(packet)
    assert len(packed["candidates"]) == 8
    assert all("irrelevant" not in r for r in packed["candidates"])


def test_persist_restore_roundtrip(tmp_path, monkeypatch):
    import state_tools
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(state_tools, "DB", tmp_path / "state" / "arena.sqlite3")
    monkeypatch.setattr(state_tools, "BACKUP", tmp_path / "state" / "arena.sqlite3.gz")
    original = arena.Ledger(state_tools.DB)
    original.initialize(1.4)
    original.set_meta("some_key", 12345)
    original.db.close()
    state_tools.save()
    state_tools.DB.unlink()
    state_tools.restore()
    with arena.Ledger(state_tools.DB).db as conn:
        value = conn.execute("SELECT value FROM meta WHERE key='some_key'").fetchone()[0]
    assert value == "12345"


def test_public_dashboard_exports_without_secrets(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    import runpy
    import dashboard
    monkeypatch.setattr(dashboard, "DB", tmp_path / "nothing.sqlite3")
    # static_export pulls source templates by its own module path; generated site is local.
    runpy.run_module("static_export", run_name="__main__")
    html = (tmp_path / "docs" / "index.html").read_text()
    data = (tmp_path / "docs" / "data.json").read_text()
    assert "./data.json" in html and "/api/state" not in html
    assert "GROQ_API_KEY" not in data and "GEMINI_API_KEY" not in data
    assert '"NOT_STARTED"' in data


def test_full_free_engine_tick_uses_only_simulated_trades(tmp_path, monkeypatch):
    from datetime import datetime, timezone
    class FakeDiscoveryMarket(FakeMarket):
        def discover(self):
            return [token("A" * 32)]
    monkeypatch.setattr(arena, "fx_cad_per_usd", lambda: 1.35)
    monkeypatch.setattr(arena, "llm_decision", lambda agent, packet: {
        "action": "HOLD", "mint": "", "usd_amount": 0, "reason": "mock AI for offline test"})
    ledger = arena.Ledger(tmp_path / "full.sqlite3")
    engine = arena.Engine(ledger, FakeDiscoveryMarket())
    engine.step()
    assert ledger.meta("started_at") is not None
    assert 6.9 * 86400 < ledger.meta("deadline") - ledger.meta("started_at") < 7.1 * 86400
    assert ledger.db.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 4
    assert ledger.db.execute("SELECT COUNT(*) FROM decisions").fetchone()[0] == 4
    assert ledger.db.execute("SELECT COUNT(*) FROM trades WHERE agent='momentum_baseline'").fetchone()[0] == 1
    for agent in arena.AGENTS:
        assert engine.portfolio_packet(agent)["exposure_percent"] <= 75.0
    # The Gemini/Groq agents held; this test makes no provider or wallet transaction.
