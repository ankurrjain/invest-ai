"""
Technical analysis tools using manual pandas calculations.
"""
import yfinance as yf
import pandas as pd
import numpy as np
from langchain_core.tools import tool
from ..utils.formatters import format_number
from ..utils.ticker import get_currency_symbol


def _history(ticker: str, period: str = "1y") -> pd.DataFrame:
    return yf.Ticker(ticker).history(period=period)


def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _macd(close: pd.Series):
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    return macd, signal, macd - signal


def _bollinger(close: pd.Series, period: int = 20, k: float = 2.0):
    sma = close.rolling(period).mean()
    std = close.rolling(period).std()
    return sma + k * std, sma, sma - k * std


@tool
def get_moving_averages(ticker: str) -> str:
    """Calculate SMA 20/50/200 and EMA 12/26. Shows price position vs each MA and golden/death cross."""
    try:
        df = _history(ticker, "1y")
        if df.empty:
            return f"No data for {ticker}"
        close = df["Close"]
        cur = get_currency_symbol(ticker)
        price = close.iloc[-1]
        sma20 = close.rolling(20).mean().iloc[-1]
        sma50 = close.rolling(50).mean().iloc[-1]
        sma200 = close.rolling(200).mean().iloc[-1] if len(close) >= 200 else None
        ema12 = close.ewm(span=12).mean().iloc[-1]
        ema26 = close.ewm(span=26).mean().iloc[-1]

        def row(name, ma):
            if ma is None or pd.isna(ma):
                return f"| {name} | N/A | — |"
            diff = (price - ma) / ma * 100
            icon = "✅" if price > ma else "❌"
            return f"| {name} | {cur}{ma:.2f} | {icon} {diff:+.2f}% |"

        cross = ""
        if sma50 and sma200 and not pd.isna(sma200):
            cross = "🔆 Golden Cross (Bullish)" if sma50 > sma200 else "💀 Death Cross (Bearish)"

        return f"""## Moving Averages — {ticker}
Current: **{cur}{price:.2f}**

| Indicator | Value | vs Price |
|-----------|-------|----------|
{row('SMA 20', sma20)}
{row('SMA 50', sma50)}
{row('SMA 200', sma200)}
{row('EMA 12', ema12)}
{row('EMA 26', ema26)}

**Cross Signal:** {cross if cross else '—'}
"""
    except Exception as e:
        return f"Error: {e}"


@tool
def get_rsi(ticker: str) -> str:
    """Calculate RSI(14). Identifies overbought (>70) and oversold (<30) conditions."""
    try:
        df = _history(ticker, "6mo")
        if df.empty:
            return f"No data for {ticker}"
        rsi = _rsi(df["Close"])
        cur_rsi = rsi.iloc[-1]
        rsi_7 = rsi.iloc[-7] if len(rsi) >= 7 else None
        rsi_30 = rsi.iloc[-30] if len(rsi) >= 30 else None

        if cur_rsi >= 70:
            signal = "🔴 OVERBOUGHT — pullback risk"
        elif cur_rsi <= 30:
            signal = "🟢 OVERSOLD — potential bounce"
        elif cur_rsi >= 60:
            signal = "🟡 Approaching overbought"
        elif cur_rsi <= 40:
            signal = "🟡 Approaching oversold"
        else:
            signal = "⚪ NEUTRAL"

        return f"""## RSI — {ticker}
- **RSI(14):** {cur_rsi:.2f}
- **Signal:** {signal}
- **7 days ago:** {f'{rsi_7:.2f}' if rsi_7 is not None else 'N/A'}
- **30 days ago:** {f'{rsi_30:.2f}' if rsi_30 is not None else 'N/A'}
"""
    except Exception as e:
        return f"Error: {e}"


@tool
def get_macd(ticker: str) -> str:
    """Calculate MACD (12/26/9). Detects trend direction and bullish/bearish crossovers."""
    try:
        df = _history(ticker, "1y")
        if df.empty:
            return f"No data for {ticker}"
        macd_l, sig_l, hist = _macd(df["Close"])
        m, s, h = macd_l.iloc[-1], sig_l.iloc[-1], hist.iloc[-1]
        trend = "🟢 BULLISH" if m > s else "🔴 BEARISH"

        crossover = ""
        for i in range(-5, -1):
            if macd_l.iloc[i-1] < sig_l.iloc[i-1] and macd_l.iloc[i] >= sig_l.iloc[i]:
                crossover = "⚡ Recent BULLISH CROSSOVER"
                break
            elif macd_l.iloc[i-1] > sig_l.iloc[i-1] and macd_l.iloc[i] <= sig_l.iloc[i]:
                crossover = "⚡ Recent BEARISH CROSSOVER"
                break

        return f"""## MACD — {ticker}
- **MACD:** {m:.4f}
- **Signal:** {s:.4f}
- **Histogram:** {h:.4f}
- **Trend:** {trend}
{crossover}
"""
    except Exception as e:
        return f"Error: {e}"


@tool
def get_bollinger_bands(ticker: str) -> str:
    """Calculate Bollinger Bands (20, 2σ). Identifies volatility and breakout signals."""
    try:
        df = _history(ticker, "6mo")
        if df.empty:
            return f"No data for {ticker}"
        upper, mid, lower = _bollinger(df["Close"])
        cur = get_currency_symbol(ticker)
        price = df["Close"].iloc[-1]
        u, m, l = upper.iloc[-1], mid.iloc[-1], lower.iloc[-1]
        bw = (u - l) / m * 100

        if price > u:
            pos = "🔴 Above upper band — overbought"
        elif price < l:
            pos = "🟢 Below lower band — oversold"
        elif price > m:
            pos = "🟡 Upper half"
        else:
            pos = "🟡 Lower half"

        vol_label = "🔇 Squeeze (low vol)" if bw < 8 else "📈 Expansion (high vol)" if bw > 20 else "📊 Normal"

        return f"""## Bollinger Bands — {ticker}
- **Upper:** {cur}{u:.2f}
- **Middle (SMA20):** {cur}{m:.2f}
- **Lower:** {cur}{l:.2f}
- **Price:** {cur}{price:.2f}
- **Band Width:** {bw:.2f}% — {vol_label}
- **Position:** {pos}
"""
    except Exception as e:
        return f"Error: {e}"


@tool
def get_full_technical_analysis(ticker: str) -> str:
    """Full technical analysis: MAs, RSI, MACD, Bollinger Bands, volume. Returns composite score."""
    try:
        df = _history(ticker, "1y")
        if df.empty:
            return f"No data for {ticker}"
        close = df["Close"]
        cur = get_currency_symbol(ticker)
        price = close.iloc[-1]

        rsi_s = _rsi(close)
        macd_l, sig_l, _ = _macd(close)
        upper, mid, lower = _bollinger(close)
        sma20 = close.rolling(20).mean().iloc[-1]
        sma50 = close.rolling(50).mean().iloc[-1]
        sma200 = close.rolling(200).mean().iloc[-1] if len(close) >= 200 else None
        cur_rsi = rsi_s.iloc[-1]
        cur_macd = macd_l.iloc[-1]
        cur_sig = sig_l.iloc[-1]
        avg_vol = df["Volume"].rolling(20).mean().iloc[-1]
        cur_vol = df["Volume"].iloc[-1]
        vol_ratio = cur_vol / avg_vol if avg_vol > 0 else 1

        score, total = 0, 0
        if cur_rsi <= 30: score += 1
        elif cur_rsi <= 70: score += 0.5
        total += 1
        if cur_macd > cur_sig: score += 1
        total += 1
        if price > sma20: score += 1
        total += 1
        if price > sma50: score += 1
        total += 1
        if sma200 is not None and not pd.isna(sma200):
            if price > sma200: score += 1
            total += 1

        pct = (score / total) * 100
        verdict = "🟢 BULLISH" if pct >= 70 else "🟡 MIXED" if pct >= 40 else "🔴 BEARISH"

        def pdiff(v2):
            if v2 is None or pd.isna(v2): return "N/A"
            return f"{(price-v2)/v2*100:+.2f}%"

        return f"""## Full Technical Analysis — {ticker}
### Signal: {verdict} ({pct:.0f}/100)
Price: **{cur}{price:.2f}**

| Metric | Value | Signal |
|--------|-------|--------|
| RSI(14) | {cur_rsi:.1f} | {'Overbought' if cur_rsi>70 else 'Oversold' if cur_rsi<30 else 'Neutral'} |
| MACD | {cur_macd:.4f} | {'Bullish' if cur_macd>cur_sig else 'Bearish'} |
| vs SMA 20 | {cur}{sma20:.2f} | {pdiff(sma20)} |
| vs SMA 50 | {cur}{sma50:.2f} | {pdiff(sma50)} |
| vs SMA 200 | {f'{cur}{sma200:.2f}' if sma200 else 'N/A'} | {pdiff(sma200)} |
| BB Position | — | {'Above upper' if price>upper.iloc[-1] else 'Below lower' if price<lower.iloc[-1] else 'Within bands'} |
| Volume | {format_number(cur_vol)} | {vol_ratio:.1f}x avg |
"""
    except Exception as e:
        return f"Error: {e}"
