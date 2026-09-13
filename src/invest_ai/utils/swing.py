"""Deterministic daily swing-trading indicator calculations.

Signals are a repeatable technical screen, not investment advice.  They use
completed daily candles where the data provider makes them available.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import yfinance as yf


def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gains = delta.clip(lower=0).ewm(alpha=1 / period, adjust=False).mean()
    losses = (-delta.clip(upper=0)).ewm(alpha=1 / period, adjust=False).mean()
    rs = gains / losses.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _adx(data: pd.DataFrame, period: int = 14) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Return ADX, +DI and -DI using Wilder smoothing."""
    high, low, close = data["High"], data["Low"], data["Close"]
    up_move, down_move = high.diff(), -low.diff()
    plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
    minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0.0)
    true_range = pd.concat(
        [high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1
    ).max(axis=1)
    atr = true_range.ewm(alpha=1 / period, adjust=False).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1 / period, adjust=False).mean() / atr.replace(0, np.nan)
    minus_di = 100 * minus_dm.ewm(alpha=1 / period, adjust=False).mean() / atr.replace(0, np.nan)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    return dx.ewm(alpha=1 / period, adjust=False).mean(), plus_di, minus_di


def get_swing_snapshot(ticker: str, horizon_days: int = 4) -> tuple[pd.DataFrame | None, dict | None, str | None]:
    """Fetch one year of daily data and return a compact, explainable signal with entry/exit levels."""
    try:
        data = yf.Ticker(ticker).history(period="1y", interval="1d", auto_adjust=True)
        if data.empty or len(data) < 60:
            return None, None, "Not enough daily price history to calculate a swing signal."

        close = data["Close"]
        data["EMA9"] = close.ewm(span=9, adjust=False).mean()
        data["EMA12"] = close.ewm(span=12, adjust=False).mean()
        data["EMA21"] = close.ewm(span=21, adjust=False).mean()
        data["EMA26"] = close.ewm(span=26, adjust=False).mean()
        data["SMA20"] = close.rolling(20).mean()
        data["SMA50"] = close.rolling(50).mean()
        data["SMA200"] = close.rolling(200).mean()
        data["RSI"] = _rsi(close)
        data["MACD"] = data["EMA12"] - data["EMA26"]
        data["MACDSignal"] = data["MACD"].ewm(span=9, adjust=False).mean()
        data["ADX"], data["PlusDI"], data["MinusDI"] = _adx(data)
        tr = pd.concat([
            data["High"] - data["Low"],
            (data["High"] - close.shift()).abs(),
            (data["Low"] - close.shift()).abs(),
        ], axis=1).max(axis=1)
        data["ATR"] = tr.ewm(alpha=1 / 14, adjust=False).mean()
        data["VolumeAvg20"] = data["Volume"].rolling(20).mean()

        last = data.iloc[-1]
        required = ["SMA20", "SMA50", "RSI", "MACD", "MACDSignal", "ADX", "PlusDI", "MinusDI", "ATR", "VolumeAvg20"]
        if last[required].isna().any():
            return data, None, "The latest indicator values are incomplete; try again after the next daily close."

        price = float(last["Close"])
        score = 0
        reasons: list[str] = []
        # Trend and momentum: a directional trend needs ADX confirmation.
        if price > last["SMA20"] > last["SMA50"]:
            score += 2; reasons.append("price is above rising short/intermediate trend averages")
        elif price < last["SMA20"] < last["SMA50"]:
            score -= 2; reasons.append("price is below falling short/intermediate trend averages")
        if not pd.isna(last["SMA200"]):
            if price > last["SMA200"]:
                score += 1; reasons.append("price is above the 200-day trend")
            else:
                score -= 1; reasons.append("price is below the 200-day trend")
        if last["MACD"] > last["MACDSignal"]:
            score += 1; reasons.append("MACD momentum is positive")
        else:
            score -= 1; reasons.append("MACD momentum is negative")
        if last["EMA9"] > last["EMA21"]:
            reasons.append("fast 9 EMA is above 21 EMA")
        if 45 <= last["RSI"] <= 68:
            score += 1; reasons.append("RSI supports momentum without being overbought")
        elif last["RSI"] >= 75:
            score -= 1; reasons.append("RSI is extended/overbought")
        elif last["RSI"] <= 30:
            reasons.append("RSI is oversold; wait for price confirmation")
        if last["ADX"] >= 20 and last["PlusDI"] > last["MinusDI"]:
            score += 1; reasons.append("ADX confirms bullish directional strength")
        elif last["ADX"] >= 20 and last["MinusDI"] > last["PlusDI"]:
            score -= 1; reasons.append("ADX confirms bearish directional strength")
        volume_ratio = float(last["Volume"] / last["VolumeAvg20"]) if last["VolumeAvg20"] else 1.0
        if volume_ratio >= 1.2:
            score += 1 if score > 0 else -1 if score < 0 else 0
            reasons.append("today's volume is above its 20-day average")

        if score >= 5:
            signal = "BUY"
        elif score >= 2:
            signal = "WATCH / BUY ON CONFIRMATION"
        elif score <= -4:
            signal = "SELL / AVOID"
        elif score <= -2:
            signal = "WATCH / REDUCE"
        else:
            signal = "NEUTRAL"

        atr = float(last["ATR"])
        h = max(2, min(int(horizon_days), 30))
        pdh = float(data["High"].iloc[-2]) if len(data) >= 2 else price
        pdl = float(data["Low"].iloc[-2]) if len(data) >= 2 else price

        # Dynamic ATR scaling based on swing horizon
        sl_mult = round(0.75 + 0.15 * (h ** 0.5), 2)
        t1_mult = round(sl_mult * 1.5, 2)
        t2_mult = round(sl_mult * 2.5, 2)

        if score >= 0:
            direction = "LONG"
            entry_price = round(max(price, pdh * 1.001), 2)
            stop_loss = round(entry_price - (sl_mult * atr), 2)
            risk_amt = max(0.01, entry_price - stop_loss)
            target_1 = round(entry_price + (t1_mult * atr), 2)
            target_2 = round(entry_price + (t2_mult * atr), 2)
            rr_ratio = round((target_1 - entry_price) / risk_amt, 2)
            risk_pct = round((risk_amt / entry_price) * 100, 2)
            t1_gain_pct = round(((target_1 - entry_price) / entry_price) * 100, 2)
            t2_gain_pct = round(((target_2 - entry_price) / entry_price) * 100, 2)
        else:
            direction = "SHORT / HEDGE"
            entry_price = round(min(price, pdl * 0.999), 2)
            stop_loss = round(entry_price + (sl_mult * atr), 2)
            risk_amt = max(0.01, stop_loss - entry_price)
            target_1 = round(entry_price - (t1_mult * atr), 2)
            target_2 = round(entry_price - (t2_mult * atr), 2)
            rr_ratio = round((entry_price - target_1) / risk_amt, 2)
            risk_pct = round((risk_amt / entry_price) * 100, 2)
            t1_gain_pct = round(((entry_price - target_1) / entry_price) * 100, 2)
            t2_gain_pct = round(((entry_price - target_2) / entry_price) * 100, 2)

        snapshot = {
            "Ticker": ticker, "Signal": signal, "Score": score, "Price": price,
            "Horizon Days": h, "Direction": direction,
            "Entry Price": entry_price, "Stop Loss": stop_loss,
            "Target 1": target_1, "Target 2": target_2,
            "Risk / Share": round(risk_amt, 2), "Risk %": risk_pct,
            "Target 1 %": t1_gain_pct, "Target 2 %": t2_gain_pct,
            "R:R Ratio": rr_ratio,
            "Time Stop": f"Exit if T1 not reached within {h} trading sessions",
            "RSI (14)": float(last["RSI"]), "ADX (14)": float(last["ADX"]),
            "+DI": float(last["PlusDI"]), "-DI": float(last["MinusDI"]),
            "MACD": float(last["MACD"]), "MACD Signal": float(last["MACDSignal"]),
            "Volume / 20d": volume_ratio, "ATR (14)": atr,
            "ATR %": (atr / price * 100), "SMA 20": float(last["SMA20"]),
            "SMA 50": float(last["SMA50"]), "SMA 200": float(last["SMA200"]) if not pd.isna(last["SMA200"]) else None,
            "EMA 9": float(last["EMA9"]), "EMA 21": float(last["EMA21"]),
            "Setup": "; ".join(reasons),
            "As of": data.index[-1].strftime("%Y-%m-%d"),
        }
        return data, snapshot, None
    except Exception as exc:
        return None, None, f"Could not retrieve {ticker}: {exc}"

