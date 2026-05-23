"""
Stock data tools using yfinance — price, company info, historical data, analyst recommendations.
"""
import yfinance as yf
from langchain_core.tools import tool
from ..utils.formatters import format_number, format_pct, safe_get
from ..utils.ticker import get_currency_symbol


def _info(ticker: str) -> dict:
    return yf.Ticker(ticker).info


@tool
def get_stock_price(ticker: str) -> str:
    """Get the current price, day range, 52-week range, volume, and market cap for a stock ticker."""
    try:
        info = _info(ticker)
        cur = get_currency_symbol(ticker)
        price = info.get("currentPrice") or info.get("regularMarketPrice")
        prev = info.get("previousClose")
        change = (price - prev) if price and prev else None
        change_pct = (change / prev * 100) if change and prev else None
        change_str = f"{change:+.2f} ({change_pct:+.2f}%)" if change is not None else "N/A"

        return f"""## Current Market Data — {ticker}
- **Price:** {cur}{format_number(price, 2)}
- **Change:** {change_str}
- **Open:** {cur}{format_number(info.get('open'), 2)}
- **Day Range:** {cur}{format_number(info.get('dayLow'), 2)} – {cur}{format_number(info.get('dayHigh'), 2)}
- **52W Range:** {cur}{format_number(info.get('fiftyTwoWeekLow'), 2)} – {cur}{format_number(info.get('fiftyTwoWeekHigh'), 2)}
- **Volume:** {format_number(info.get('volume'))}
- **Avg Volume (10d):** {format_number(info.get('averageVolume10days'))}
- **Market Cap:** {cur}{format_number(info.get('marketCap'))}
- **Beta:** {format_number(info.get('beta'))}
"""
    except Exception as e:
        return f"Error fetching price for {ticker}: {e}"


@tool
def get_company_info(ticker: str) -> str:
    """Get company name, sector, industry, country, employee count, and business description."""
    try:
        info = _info(ticker)
        desc = info.get("longBusinessSummary", "No description available.")
        if len(desc) > 800:
            desc = desc[:800] + "..."
        return f"""## Company Profile — {info.get('longName', ticker)}
- **Symbol:** {ticker}
- **Exchange:** {safe_get(info, 'exchange')}
- **Sector:** {safe_get(info, 'sector')}
- **Industry:** {safe_get(info, 'industry')}
- **Country:** {safe_get(info, 'country')}
- **Employees:** {format_number(info.get('fullTimeEmployees'), 0)}
- **Website:** {safe_get(info, 'website')}
- **Currency:** {safe_get(info, 'currency')}

**Business Summary:**
{desc}
"""
    except Exception as e:
        return f"Error fetching company info for {ticker}: {e}"


@tool
def get_analyst_recommendations(ticker: str) -> str:
    """Get analyst consensus rating, price targets, and recent recommendation history."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        cur = get_currency_symbol(ticker)

        result = f"""## Analyst Recommendations — {ticker}
- **Consensus:** {str(info.get('recommendationKey', 'N/A')).upper()}
- **# of Analysts:** {safe_get(info, 'numberOfAnalystOpinions')}
- **Mean Target:** {cur}{format_number(info.get('targetMeanPrice'), 2)}
- **High Target:** {cur}{format_number(info.get('targetHighPrice'), 2)}
- **Low Target:** {cur}{format_number(info.get('targetLowPrice'), 2)}
"""
        try:
            recs = stock.recommendations
            if recs is not None and not recs.empty:
                result += "\n**Recent Actions (last 5):**\n"
                result += recs.tail(5).to_string()
        except Exception:
            pass
        return result
    except Exception as e:
        return f"Error fetching recommendations for {ticker}: {e}"


@tool
def get_historical_data(ticker: str, period: str = "1y") -> str:
    """
    Get historical OHLCV data summary for a ticker.
    Period options: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y.
    Returns a summary with period return, highs/lows, and recent 5 days.
    """
    try:
        hist = yf.Ticker(ticker).history(period=period)
        if hist.empty:
            return f"No historical data available for {ticker}"

        cur = get_currency_symbol(ticker)
        latest = hist.iloc[-1]
        oldest = hist.iloc[0]
        ret = ((latest["Close"] - oldest["Close"]) / oldest["Close"]) * 100

        result = f"""## Historical Data — {ticker} ({period})
- **Period:** {hist.index[0].strftime('%Y-%m-%d')} → {hist.index[-1].strftime('%Y-%m-%d')}
- **Start Price:** {cur}{oldest['Close']:.2f}
- **End Price:** {cur}{latest['Close']:.2f}
- **Period Return:** {ret:+.2f}%
- **Period High:** {cur}{hist['High'].max():.2f}
- **Period Low:** {cur}{hist['Low'].min():.2f}
- **Avg Daily Volume:** {format_number(hist['Volume'].mean())}
- **Trading Days:** {len(hist)}

**Last 5 Days:**
{hist.tail(5)[['Open','High','Low','Close','Volume']].round(2).to_string()}
"""
        return result
    except Exception as e:
        return f"Error fetching historical data for {ticker}: {e}"


@tool
def compare_stocks(tickers: str) -> str:
    """
    Compare key metrics for multiple stocks side by side.
    Pass tickers as a comma-separated string e.g. 'AAPL,MSFT,GOOGL' or 'RELIANCE.NS,TCS.NS'.
    """
    try:
        ticker_list = [t.strip().upper() for t in tickers.split(",")]
        rows = []
        for t in ticker_list:
            try:
                info = yf.Ticker(t).info
                cur = get_currency_symbol(t)
                price = info.get("currentPrice") or info.get("regularMarketPrice")
                rows.append({
                    "Ticker": t,
                    "Price": f"{cur}{format_number(price, 2)}",
                    "Mkt Cap": format_number(info.get("marketCap")),
                    "P/E": format_number(info.get("trailingPE")),
                    "Fwd P/E": format_number(info.get("forwardPE")),
                    "52W Return": "N/A",
                    "Div Yield": format_pct(info.get("dividendYield")),
                    "Sector": safe_get(info, "sector"),
                })
            except Exception:
                rows.append({"Ticker": t, "Price": "Error"})

        import pandas as pd
        df = pd.DataFrame(rows).set_index("Ticker")
        return f"## Stock Comparison\n{df.to_markdown()}"
    except Exception as e:
        return f"Error comparing stocks: {e}"
