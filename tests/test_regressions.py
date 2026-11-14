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
