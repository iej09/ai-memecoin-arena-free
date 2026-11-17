"""Additional deployment/readiness regressions for the zero-cost arena."""
import sys
import time
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tournament as a


def tok(mint):
    return {"id": mint, "name": "coin", "symbol": "X", "tokenProgram": a.SPL_TOKEN_PROGRAM,
            "decimals": 6, "liquidity": 100000, "organicScore": 80,
            "holderCount": 1000, "audit": {"isSus": False, "mintAuthorityDisabled": True,
            "freezeAuthorityDisabled": True, "topHoldersPercentage": 8},
            "stats5m": {"priceChange": 5, "numBuys": 400, "numSells": 100},
            "stats1h": {"priceChange": 10}}


def test_malformed_metadata_does_not_abort_all_candidates():
    assert not a.eligible({**tok('A'*32), 'decimals': 'junk'})
    assert not a.eligible({**tok('A'*32), 'audit': []})
    assert not a.eligible({**tok('A'*32), 'decimals': True})


def test_same_candidate_count_for_all_bots(tmp_path):
    class Market:
        def discover(self):
            return [tok(chr(65+i)*32) for i in range(15)]
    e=a.Engine(a.Ledger(tmp_path/'fair.db'), Market())
    tokens,m=e.market_packet()
    assert len(tokens) == a.MAX_CANDIDATES == 8
    assert set(m)=={t['id'] for t in tokens}
    for agent in a.AGENTS:
        packet={'candidates':tokens,'portfolio':{'cash_usd':100,'holdings':[],'equity_usd':100}}
        assert len(a.compact_free_packet(packet)['candidates']) == len(packet['candidates'])


def test_first_run_without_eligible_data_does_not_start(tmp_path, monkeypatch):
    class Market:
        def discover(self):
            return []
        def quote(self, *args):
            return None
    monkeypatch.setattr(a, 'fx_cad_per_usd', lambda: 1.35)
    ledger=a.Ledger(tmp_path/'empty.db')
    e=a.Engine(ledger, Market())
    e.step()
    assert ledger.meta('started_at') is None
    assert ledger.meta('last_market_status') in ('NO_ELIGIBLE_TOKENS','MARKET_UNAVAILABLE')
    assert ledger.meta('last_healthy_tick') is None


def test_outage_after_start_cannot_be_healthy_tick(tmp_path, monkeypatch):
    class Market:
        def discover(self):
            raise OSError('offline')
        def quote(self, *args):
            return None
    monkeypatch.setattr(a, 'fx_cad_per_usd', lambda: 1.35)
    ledger=a.Ledger(tmp_path/'outage.db')
    ledger.initialize(1.35)
    e=a.Engine(ledger,Market())
    e.step()
    assert ledger.meta('last_heartbeat')
    assert ledger.meta('last_healthy_tick') is None
    assert ledger.meta('last_market_status') == 'MARKET_UNAVAILABLE'


def test_missing_fx_before_start_prevents_timer(tmp_path,monkeypatch):
    class Market:
        pass
    def no_fx():
        raise OSError('no fx')
    monkeypatch.setattr(a, 'fx_cad_per_usd', no_fx)
    ledger=a.Ledger(tmp_path/'fx.db')
    e=a.Engine(ledger,Market())
    e.step()
    assert ledger.meta('started_at') is None
    assert ledger.meta('fx_status') == 'UNAVAILABLE'


def test_stale_fx_after_start_is_explicit(tmp_path,monkeypatch):
    class Market:
        def discover(self):
            raise OSError('offline')
        def quote(self, *args):
            return None
    def no_fx():
        raise OSError('no fx')
    monkeypatch.setattr(a, 'fx_cad_per_usd', no_fx)
    ledger=a.Ledger(tmp_path/'fx-stale.db')
    ledger.initialize(1.4)
    ledger.set_meta('last_fx',1.4)
    e=a.Engine(ledger,Market())
    e.step()
    assert ledger.meta('fx_status') == 'LAST_KNOWN'
    assert ledger.meta('started_at') is not None


def test_groq_model_specific_reasoning_options(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "unit-test-not-a-key")
    seen = {}
    sample = '{"action":"HOLD","mint":"","usd_amount":0,"research_type":"ALL","reason":"test"}'
    def mock_request(method, url, **kwargs):
        seen[kwargs["body"]["model"]] = kwargs["body"]
        return {"choices":[{"message":{"content":sample}}]}
    monkeypatch.setattr(a,"http_json", mock_request)
    for model in ("groq_gptoss", "groq_qwen"):
        assert a.llm_decision(model,{"candidates": []})["action"] == "HOLD"
    assert "reasoning_format" not in seen["openai/gpt-oss-120b"]
    assert seen["qwen/qwen3.8-27b"]["reasoning_format"] == "hidden"
    assert all(x["response_format"]["json_schema"]["strict"] for x in seen.values())


def test_complete_seven_day_paper_run_and_final_csv(tmp_path, monkeypatch):
    """Run through opening trades to the deadline with simulated AI replies."""
    now = 1_800_000_000.0
    monkeypatch.setattr(a.time, "time", lambda: now)
    monkeypatch.setattr(a, "fx_cad_per_usd", lambda: 1.4)
    monkeypatch.setattr(a, "RESULTS_DIR", tmp_path / "exports")
    class Market:
        def discover(self):
            return [tok('A' * 32)]
        def quote(self, in_mint, out_mint, amount):
            if in_mint == a.USDC:
                return amount * 2
            if out_mint == a.USDC:
                return amount // 2
            return None
    def decisions(agent, packet):
        if agent == "gemini_free" and not packet["portfolio"]["holdings"]:
            return {"action": "BUY", "mint": 'A' * 32, "usd_amount": 150, "reason": "mock buy"}
        return {"action": "HOLD", "mint": "", "usd_amount": 0, "reason": "mock hold"}
    monkeypatch.setattr(a, "llm_decision", decisions)
    ledger = a.Ledger(tmp_path / 'final.sqlite3')
    engine = a.Engine(ledger, Market())
    engine.step()
    started_at = ledger.meta('started_at')
    assert started_at == now
    assert ledger.meta('deadline') == now + 7 * 86400
    assert ledger.db.execute('SELECT COUNT(*) FROM holdings').fetchone()[0] > 0
    now += 7 * 86400 + 1
    engine.step()
    assert ledger.meta('finished') is True
    assert ledger.db.execute('SELECT COUNT(*) FROM holdings').fetchone()[0] == 0
    assert (tmp_path / 'exports' / 'trades.csv').is_file()
    assert ledger.meta('deadline') == started_at + 7 * 86400


def test_jupiter_quote_never_requests_a_real_transaction(monkeypatch):
    j = a.Jupiter()
    observed = {}
    def get(path, params):
        observed.update(path=path, params=params)
        return {'outAmount': '123400'}
    monkeypatch.setattr(j, 'get', get)
    assert j.quote(a.USDC, 'A' * 32, 1000000) == 123400
    assert observed['path'] == '/swap/v2/order'
    assert observed['params'].get('taker') is None
    assert observed['params'].get('userPublicKey') is None
    assert 'transaction' not in str(observed).lower()


def test_risk_filter_rejects_missing_authorities_and_extreme_holder_concentration():
    base = tok('A' * 32)
    for patch in (
        {'audit': {'mintAuthorityDisabled': True, 'freezeAuthorityDisabled': True}},
        {'audit': {**base['audit'], 'topHoldersPercentage': 77}},
        {'audit': {**base['audit'], 'freezeAuthorityDisabled': False}},
        {'organicScore': 0},
        {'liquidity': 1},
    ):
        assert not a.eligible({**base, **patch})


def test_bad_ai_request_cannot_invest_more_than_cash(tmp_path):
    class Market:
        def quote(self, im, om, amt):
            return amt * 2 if im == a.USDC else amt // 2
    ledger = a.Ledger(tmp_path / 'risk.sqlite3')
    ledger.initialize(1.4)
    engine = a.Engine(ledger, Market())
    token = tok('A' * 32)
    for n in range(4):
        key = chr(65 + n) * 32
        coin = {**token, 'id': key}
        engine.execute('gemini_free', {'action': 'BUY', 'mint': key, 'usd_amount': 10_000_000}, {key: coin})
        assert ledger.portfolio('gemini_free')['cash_usd'] >= -0.000001
        assert engine.portfolio_packet('gemini_free')['exposure_percent'] <= 100.01


def test_repository_fallback_scoreboard_is_public_safe(tmp_path, monkeypatch):
    import runpy
    import dashboard
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(dashboard, "DB", tmp_path / "none.sqlite3")
    runpy.run_module("static_export", run_name="__main__")
    status = (tmp_path / "STATUS.md").read_text()
    assert "NOT_STARTED" in status
    assert "\n" in status
    assert "GEMINI_API_KEY" not in status and "GROQ_API_KEY" not in status


def test_gemini_uses_supported_json_schema_response_configuration(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "unit-test-not-a-key")
    sent = {}
    def mock_request(method, url, **kwargs):
        sent.update({"method": method, "url": url, **kwargs})
        return {"candidates": [{"content": {"parts": [{"text": '{"action":"HOLD","mint":"","usd_amount":0,"research_type":"ALL","reason":"test"}'}]}}]}
    monkeypatch.setattr(a, "http_json", mock_request)
    assert a.llm_decision("gemini_free", {"candidates": []})["action"] == "HOLD"
    config = sent["body"]["generationConfig"]
    assert config["responseMimeType"] == "application/json"
    assert config["responseJsonSchema"] == a.DECISION_SCHEMA
    assert config["thinkingConfig"]["thinkingLevel"] == "MINIMAL"
    assert "temperature" not in config
    assert "responseSchema" not in config



def test_all_in_can_stay_invested_above_old_75_percent_limit(tmp_path):
    class Market:
        def quote(self, im, om, amt):
            return amt * 2 if im == a.USDC else amt // 2
    ledger = a.Ledger(tmp_path / "all-in-risk.sqlite3")
    ledger.initialize(1.4)
    engine = a.Engine(ledger, Market())
    token = tok("A" * 32)
    ok, msg = engine.execute(
        "groq_gptoss", {"action":"BUY", "mint":token["id"], "usd_amount": 1_000_000},
        {token["id"]:token})
    assert ok, msg
    assert engine.portfolio_packet("groq_gptoss")["exposure_percent"] > 99.9
    engine.risk_controls("groq_gptoss")
    assert engine.portfolio_packet("groq_gptoss")["exposure_percent"] > 99.9
    assert ledger.portfolio("groq_gptoss")["cash_usd"] >= 0


def test_preflight_checks_all_agents_and_does_not_start_if_one_provider_fails(tmp_path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "mock-free-key")
    monkeypatch.setenv("GROQ_API_KEY", "mock-free-key")
    monkeypatch.setattr(a, "DB_PATH", tmp_path / "preflight.db")
    monkeypatch.setattr(a, "fx_cad_per_usd", lambda: 1.4)
    class PublicMarket:
        def discover(self):
            return [tok("A" * 32)]
    monkeypatch.setattr(a, "Jupiter", lambda: PublicMarket())
    seen = []
    def fake_model(provider, packet):
        seen.append(provider)
        if provider == "gemini_free":
            raise RuntimeError("mock provider outage")
        return {"action": "HOLD", "mint": "", "reason": "mock ok"}
    monkeypatch.setattr(a, "llm_decision", fake_model)
    monkeypatch.setattr(a.sys, "argv", ["tournament.py", "--check"])
    with pytest.raises(RuntimeError, match="Preflight failed for: gemini_free"):
        a.main()
    assert seen == list(a.MODELS)
    ledger = a.Ledger(tmp_path / "preflight.db")
    assert ledger.meta("started_at") is None


def test_groq_429_uses_retry_after_and_succeeds(monkeypatch):
    import requests
    monkeypatch.setenv("GROQ_API_KEY", "unit-test-free-key")
    response = requests.Response()
    response.status_code = 429
    response.headers["Retry-After"] = "4"
    calls = []
    sleeps = []
    result = '{"action":"HOLD","mint":"","usd_amount":0,"research_type":"ALL","reason":"OK"}'
    def stub_request(method, url, **kwargs):
        calls.append(url)
        if len(calls) == 1:
            raise requests.HTTPError("429 Too Many Requests", response=response)
        return {"choices": [{"message": {"content": result}}]}
    monkeypatch.setattr(a, "http_json", stub_request)
    monkeypatch.setattr(a.time, "sleep", lambda seconds: sleeps.append(seconds))
    assert a.llm_decision("groq_qwen", {"candidates": []})["action"] == "HOLD"
    assert len(calls) == 2
    assert sleeps == [4.0]


def test_live_candidate_packet_reduces_free_tier_token_cost():
    import json
    candidates = []
    for i in range(8):
        candidates.append({
            **tok(chr(65+i)*32),
            "name": "extremely long untrusted token name " * 25,
            "stats5m": {"priceChange": 3, "numBuys": 3, "numSells": 2,
                         "unimportant": "u" * 4000},
            "audit": {**tok("A"*32)["audit"], "unimportant": "x" * 4000}
        })
    result = a.compact_free_packet({"candidates": candidates})
    assert len(result["candidates"]) == 8
    assert all("unimportant" not in x["stats5m"] for x in result["candidates"])
    assert all(len(x["name"]) <= 70 for x in result["candidates"])
    assert len(json.dumps(result)) < 7000


def test_public_scoreboard_flags_groq_api_error_separately_from_hold(tmp_path, monkeypatch):
    import runpy
    import dashboard
    ledger = a.Ledger(tmp_path / "health.sqlite3")
    ledger.initialize(1.4)
    ledger.decision("groq_gptoss", {"action": "HOLD", "reason": "API failure"},
                    False, "429 Client Error: Too Many Requests", {"candidates": []})
    for agent in a.AGENTS:
        ledger.snapshot(agent, 1000/1.4, 0, 1.4, 0)
    ledger.db.close()
    monkeypatch.setattr(dashboard, "DB", tmp_path / "health.sqlite3")
    state = dashboard.data()
    gptoss = next(x for x in state["scoreboard"] if x["agent"] == "groq_gptoss")
    assert gptoss["last_decision_health"] == "API_ERROR"
    assert gptoss["last_decision"] == "HOLD"
    gemini = next(x for x in state["scoreboard"] if x["agent"] == "gemini_free")
    assert gemini["last_decision_health"] == "PENDING"
    monkeypatch.chdir(tmp_path)
    runpy.run_module("static_export", run_name="__main__")
    assert "API ERROR" in (tmp_path / "STATUS.md").read_text()


def test_clock_based_ai_cadence_survives_skipped_github_runs(tmp_path, monkeypatch):
    fake_time = [1800000000.]
    monkeypatch.setattr(a.time, "time", lambda: fake_time[0])
    monkeypatch.setattr(a, "fx_cad_per_usd", lambda: 1.4)
    class Market:
        def discover(self):
            return [tok("A" * 32)]
        def quote(self, input_mint, output_mint, amount):
            return amount * 2 if input_mint == a.USDC else amount // 2
    calls = []
    def fake_ai(agent, packet):
        calls.append((agent, fake_time[0]))
        return {"action": "HOLD", "mint": "", "usd_amount": 0, "reason": "mock"}
    monkeypatch.setattr(a, "llm_decision", fake_ai)
    ledger = a.Ledger(tmp_path / "tick-cadence.sqlite3")
    engine = a.Engine(ledger, Market())
    engine.step()
    original_start = ledger.meta("started_at")
    assert len(calls) == len(a.MODELS)
    fake_time[0] += 900
    engine.step()
    assert len(calls) == len(a.MODELS)
    fake_time[0] += 4000
    engine.step()
    assert len(calls) == 2 * len(a.MODELS)
    assert ledger.meta("started_at") == original_start
    assert ledger.meta("deadline") == original_start + 7*86400
