"""
Ticker resolution utilities for Indian and US stock markets.
Indian stocks on NSE use .NS suffix, BSE use .BO suffix.
"""

KNOWN_INDIAN_STOCKS = {
    "RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "INFY", "SBIN", "HINDUNILVR",
    "BAJFINANCE", "BHARTIARTL", "KOTAKBANK", "ASIANPAINT", "AXISBANK",
    "MARUTI", "TITAN", "SUNPHARMA", "ULTRACEMCO", "WIPRO", "NTPC",
    "POWERGRID", "TECHM", "HCLTECH", "LT", "ADANIENT", "ADANIPORTS",
    "TATAMOTORS", "TATASTEEL", "ONGC", "JSWSTEEL", "M&M", "NESTLEIND",
    "DIVISLAB", "DRREDDY", "CIPLA", "EICHERMOT", "HEROMOTOCO", "GRASIM",
    "INDUSINDBK", "SBILIFE", "HDFCLIFE", "BAJAJFINSV", "BPCL", "COALINDIA",
    "ITC", "BRITANNIA", "PIDILITIND", "HAVELLS", "VOLTAS", "GODREJCP",
    "DABUR", "MARICO", "TATACONSUM", "NYKAA", "ZOMATO", "PAYTM",
    "DMART", "IRCTC", "POLICYBZR", "VEDL", "HINDALCO", "SAIL",
    "RECLTD", "PFC", "IRFC", "BANKBARODA", "PNB", "CANBK",
}


def resolve_ticker(ticker: str, market: str = "auto") -> str:
    """
    Resolve a ticker symbol to the correct yfinance format.
    - India (NSE): append .NS if not already suffixed
    - India (BSE): append .BO
    - US: use as-is
    """
    ticker = ticker.upper().strip()

    # Already has a suffix — return as-is
    if ticker.endswith(".NS") or ticker.endswith(".BO"):
        return ticker

    if market.lower() == "india":
        return f"{ticker}.NS"
    elif market.lower() == "india_bse":
        return f"{ticker}.BO"
    elif market.lower() == "us":
        return ticker
    else:
        # Auto-detect: if it looks like a known Indian stock, add .NS
        if ticker in KNOWN_INDIAN_STOCKS:
            return f"{ticker}.NS"
        return ticker


def detect_market(ticker: str) -> str:
    """Auto-detect the market for a given ticker."""
    t = ticker.upper().strip()
    if t.endswith(".NS"):
        return "india"
    if t.endswith(".BO"):
        return "india_bse"
    base = t.replace(".NS", "").replace(".BO", "")
    if base in KNOWN_INDIAN_STOCKS:
        return "india"
    return "us"


def get_currency_symbol(ticker: str) -> str:
    """Return the currency symbol for a given ticker."""
    t = ticker.upper()
    if t.endswith(".NS") or t.endswith(".BO"):
        return "₹"
    market = detect_market(ticker)
    if market in ("india", "india_bse"):
        return "₹"
    return "$"
