"""Price fetcher — retrieve current/close price for tickers across markets.

Markets supported:
  CN      → Tencent Finance API (qt.gtimg.cn)
  HK      → Tencent Finance API (qt.gtimg.cn)
  US      → Yahoo Finance (finance.yahoo.com) via HTTP
  CRYPTO  → Binance REST API (api.binance.com)
  FUTURES → (placeholder, requires data feed)
"""

import re
import math
import httpx
from datetime import datetime, timezone
from typing import Optional, Tuple

# ── Market prefix map ─────────────────────────────────────

CN_PREFIX = {
    "sh": "sh", "sz": "sz", "bj": "bj",
    "600": "sh", "601": "sh", "603": "sh", "605": "sh", "688": "sh",
    "000": "sz", "001": "sz", "002": "sz", "003": "sz",
    "300": "sz", "301": "sz",
    "8": "bj", "4": "bj",
}

BINANCE_SYMBOL_MAP = {
    "BTC": "BTCUSDT", "ETH": "ETHUSDT", "BNB": "BNBUSDT",
    "SOL": "SOLUSDT", "XRP": "XRPUSDT", "ADA": "ADAUSDT",
    "DOGE": "DOGEUSDT", "DOT": "DOTUSDT", "AVAX": "AVAXUSDT",
    "LINK": "LINKUSDT", "MATIC": "MATICUSDT", "UNI": "UNIUSDT",
    "ATOM": "ATOMUSDT", "LTC": "LTCUSDT", "FIL": "FILUSDT",
    "ARB": "ARBUSDT", "OP": "OPUSDT", "SUI": "SUIUSDT",
}


def _cn_exchange(ticker: str) -> str:
    """Detect CN exchange prefix: sh / sz / bj."""
    ticker = ticker.upper().strip()
    for k, v in CN_PREFIX.items():
        if ticker.startswith(k):
            return v
    # Default to SH for 6-digit codes
    if len(ticker) == 6:
        if ticker.startswith("6"):
            return "sh"
        return "sz"
    return "sh"


async def fetch_price(
    market: str,
    ticker: str,
) -> Optional[Tuple[float, float]]:
    """Fetch (current_price, price_change_pct). Returns None on failure.

    Args:
        market: CN | HK | US | CRYPTO | FUTURES
        ticker: symbol (e.g. '000001', 'AAPL', 'BTC')
    Returns:
        (price, change_pct) or None
    """
    market = market.upper().strip()
    ticker = ticker.upper().strip()

    try:
        if market == "CN":
            return await _cn_price(ticker)
        elif market == "HK":
            return await _hk_price(ticker)
        elif market == "US":
            return await _us_price(ticker)
        elif market == "CRYPTO":
            return await _crypto_price(ticker)
        elif market == "FUTURES":
            return await _futures_price(ticker)
        else:
            return None
    except Exception as e:
        print(f"[price_fetcher] Error fetching {market}:{ticker}: {e}")
        return None


async def fetch_close_price(
    market: str,
    ticker: str,
    target_date: datetime,
) -> Optional[float]:
    """Fetch closing price for a specific date.

    优先使用免费的历史数据 API（如可用），否则回退到实时价格。
    """
    # 尝试从 Sina/腾讯获取历史数据
    try:
        if market == 'CN':
            # 腾讯历史K线 API
            exchange = _cn_exchange(ticker)
            url = f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?_var=kline_dayqfq&param={exchange}{ticker},day,{target_date.strftime('%Y-%m-%d')},{target_date.strftime('%Y-%m-%d')},10,qfq&r=0.1"
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                text = resp.text
                # 解析返回数据
                import json as json_lib
                # 格式: kline_dayqfq={{...}}
                data_str = text.split('=', 1)[1] if '=' in text else '{}'
                data = json_lib.loads(data_str)
                day_data = data.get('data', {}).get(f'{exchange}{ticker}', {}).get('day', [])
                if day_data and len(day_data) > 0:
                    # 返回第一天的收盘价
                    return float(day_data[0][1])
        elif market == 'US':
            # Yahoo Finance 历史数据
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
            params = {
                'period1': int(target_date.timestamp()),
                'period2': int(target_date.timestamp()) + 86400,
                'interval': '1d'
            }
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
                result = data.get('chart', {}).get('result', [])
                if result:
                    closes = result[0].get('indicators', {}).get('quote', [{}])[0].get('close', [])
                    if closes and closes[0]:
                        return float(closes[0])
    except Exception as e:
        print(f"[price_fetcher] 历史价格获取失败 {market}:{ticker} on {target_date}: {e}")

    # 回退到当前价格
    result = await fetch_price(market, ticker)
    if result:
        return result[0]
    return None


# ── Market-specific fetchers ──────────────────────────────

async def _cn_price(ticker: str) -> Optional[Tuple[float, float]]:
    """Fetch CN A-share price via Tencent API."""
    exchange = _cn_exchange(ticker)
    url = f"http://qt.gtimg.cn/q={exchange}{ticker}"
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        text = resp.text

    # Format: v_sh600000="1~浦发银行~...~current_price~...~change_pct~..."
    match = re.search(r'~([\d.]+)~([\d.]+)~', text)
    if not match:
        return None
    price = float(match.group(1))
    change_pct = float(match.group(2))
    return price, change_pct


async def _hk_price(ticker: str) -> Optional[Tuple[float, float]]:
    """Fetch HK stock price via Tencent API."""
    # HK stocks use hk prefix
    url = f"http://qt.gtimg.cn/q=hk{ticker}"
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        text = resp.text

    match = re.search(r'~([\d.]+)~([\d.]+)~', text)
    if not match:
        return None
    price = float(match.group(1))
    change_pct = float(match.group(2))
    return price, change_pct


async def _us_price(ticker: str) -> Optional[Tuple[float, float]]:
    """Fetch US stock price via Yahoo Finance."""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
    headers = {"User-Agent": "Mozilla/5.0"}
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    meta = data["chart"]["result"][0]["meta"]
    price = meta["regularMarketPrice"]
    prev_close = meta["chartPreviousClose"]
    change_pct = ((price - prev_close) / prev_close) * 100 if prev_close else 0
    return price, change_pct


async def _crypto_price(ticker: str) -> Optional[Tuple[float, float]]:
    """Fetch crypto price via Binance API."""
    symbol = BINANCE_SYMBOL_MAP.get(ticker, f"{ticker}USDT")
    url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}"
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()

    price = float(data["lastPrice"])
    change_pct = float(data["priceChangePercent"])
    return price, change_pct


async def _futures_price(ticker: str) -> Optional[Tuple[float, float]]:
    """获取国内期货价格（通过新浪财经）"""
    # 期货代码映射
    futures_map = {
        'IF': 'IF0',  # 沪深300股指
        'IC': 'IC0',  # 中证500股指
        'IH': 'IH0',  # 上证50股指
        'IM': 'IM0',  # 中证1000股指
    }
    code = futures_map.get(ticker.upper(), ticker.upper())
    url = f"http://qt.gtimg.cn/q=nf_{code}"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            text = resp.text

        # 格式: nf_IF0="1~IF当月连续~...~最新价~涨跌幅~..."
        match = re.search(r'"([^"]+)"', text)
        if match:
            parts = match.group(1).split('~')
            if len(parts) > 32:
                price = float(parts[32]) if parts[32] else 0
                change_pct = float(parts[33]) if parts[33] else 0
                if price > 0:
                    return price, change_pct
    except Exception as e:
        print(f"[price_fetcher] 期货价格获取失败 {ticker}: {e}")
    return None
