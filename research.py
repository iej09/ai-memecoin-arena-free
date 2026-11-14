"""Optional, read-only discovery and diligence adapters.

A provider failure is explicit missing data, never a fabricated zero-risk signal.
All external snippets are UNTRUSTED and must not be obeyed as agent instructions.
"""
from __future__ import annotations

import os
import re
import time
from typing import Any

import requests

MINT_RE = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")
CACHE: dict[tuple, tuple[float, Any]] = {}


def valid_mint(mint: str) -> bool:
    return isinstance(mint, str) and bool(MINT_RE.fullmatch(mint))


def fetch(url: str, headers: dict | None = None, params: dict | None = None, timeout=11):
    r = requests.get(url, params=params, headers=headers or {}, timeout=timeout)
    r.raise_for_status()
    return r.json()


def cached(key: tuple, ttl: int, fn):
    now = time.monotonic()
    if key in CACHE and now < CACHE[key][0]:
        return CACHE[key][1]
    data = fn()
    CACHE[key] = (now + ttl, data)
    return data


def birdeye_new_mints() -> list[str]:
    # The free edition never calls Birdeye's possibly paid API.
    return []


def dex_pair(mint: str) -> dict[str, Any]:
    if not valid_mint(mint):
        return {"status": "invalid_mint"}

    def pull():
        rows = fetch(f"https://api.dexscreener.com/token-pairs/v1/solana/{mint}")
        if not isinstance(rows, list):
            return {"status": "unavailable"}
        matches = [x for x in rows if (x.get("baseToken") or {}).get("address") == mint]
        if not matches:
            return {"status": "no_base_token_pair"}
        x = max(matches, key=lambda z: float((z.get("liquidity") or {}).get("usd") or 0))
        info = x.get("info") or {}
        return {
            "status": "ok", "dex": str(x.get("dexId", ""))[:40],
            "pair_url": str(x.get("url", ""))[:240],
            "pair_created_ms": x.get("pairCreatedAt"),
            "liquidity_usd": (x.get("liquidity") or {}).get("usd"),
            "price_usd": x.get("priceUsd"),
            "market_cap_usd": x.get("marketCap"),
            "volume_usd": x.get("volume"),
            "buys_sells": x.get("txns"),
            "price_change_pct": x.get("priceChange"),
            "paid_boosts_active": (x.get("boosts") or {}).get("active", 0),
            "socials": [dict(platform=s.get("type") or s.get("platform"), url=s.get("url"))
                        for s in (info.get("socials") or [])[:6]],
        }
    try:
        return cached(("dex", mint), 90, pull)
    except Exception as e:
        return {"status": "unavailable", "error": type(e).__name__}


def rugcheck(mint: str) -> dict[str, Any]:
    if not valid_mint(mint):
        return {"status": "invalid_mint"}

    def pull():
        data = fetch(f"https://api.rugcheck.xyz/v1/tokens/{mint}/report", timeout=14)
        risks = data.get("risks") or []
        return {
            "status": "ok", "score_normalised": data.get("score_normalised"),
            "mint_authority": data.get("mintAuthority"),
            "freeze_authority": data.get("freezeAuthority"),
            "total_holders": data.get("totalHolders"),
            "total_market_liquidity_usd": data.get("totalMarketLiquidity"),
            "top_holders": [{"pct": x.get("pct"), "insider": x.get("insider")}
                            for x in (data.get("topHolders") or [])[:10]],
            "risks": [{"name": str(x.get("name", ""))[:100],
                       "level": str(x.get("level", ""))[:20],
                       "description": str(x.get("description", ""))[:250]}
                      for x in risks[:12]],
        }
    try:
        return cached(("rug", mint), 300, pull)
    except Exception as e:
        return {"status": "unavailable", "error": type(e).__name__}


def x_mentions(mint: str) -> dict[str, Any]:
    # The free edition never calls X's paid API.
    return {"status": "invalid_mint" if not valid_mint(mint) else "disabled_free_trial"}


def helius_holders(mint: str) -> dict[str, Any]:
    # The free edition never calls Helius's possibly paid RPC.
    return {"status": "invalid_mint" if not valid_mint(mint) else "disabled_free_trial"}


def deep_research(mint: str, kind: str = "ALL") -> dict[str, Any]:
    """An agent may request one of these bounded research bundles per decision."""
    kind = str(kind).upper()
    info: dict[str, Any] = {"mint": mint, "kind": kind, "sources": {}}
    if kind in ("ALL", "MARKET"):
        info["sources"]["dexscreener"] = dex_pair(mint)
    if kind in ("ALL", "RISK", "WALLET"):
        info["sources"]["rugcheck"] = rugcheck(mint)
        info["sources"]["helius_holders"] = helius_holders(mint)
    if kind in ("ALL", "SOCIAL"):
        info["sources"]["x"] = x_mentions(mint)
    return info
