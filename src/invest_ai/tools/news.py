"""
News and sentiment tools using DuckDuckGo search — no API key required.
"""
from langchain_core.tools import tool
from ddgs import DDGS


@tool
def search_stock_news(query: str) -> str:
    """
    Search for recent news about a stock or company using DuckDuckGo.
    Pass a query like 'RELIANCE Industries latest news' or 'Apple AAPL earnings 2024'.
    Returns the top 8 headlines with snippets and URLs.
    """
    try:
        results = []
        with DDGS() as ddgs:
            for r in ddgs.news(query, max_results=8):
                results.append(r)

        if not results:
            return f"No recent news found for: {query}"

        output = f"## News Search Results: {query}\n\n"
        for i, r in enumerate(results, 1):
            date = r.get("date", "")[:10]
            title = r.get("title", "No title")
            body = r.get("body", "")[:200]
            url = r.get("url", "")
            source = r.get("source", "")
            output += f"**{i}. [{title}]({url})**\n"
            output += f"   *{source} — {date}*\n"
            output += f"   {body}...\n\n"

        return output
    except Exception as e:
        return f"Error searching news for '{query}': {e}"


@tool
def get_market_news(market: str = "india") -> str:
    """
    Get general market news for Indian or US stock markets.
    Pass 'india' for NSE/BSE news or 'us' for NYSE/NASDAQ news.
    """
    try:
        if market.lower() == "india":
            query = "Indian stock market NSE BSE Sensex Nifty today"
        else:
            query = "US stock market NYSE NASDAQ S&P 500 today"

        results = []
        with DDGS() as ddgs:
            for r in ddgs.news(query, max_results=6):
                results.append(r)

        if not results:
            return f"No market news found for: {market}"

        output = f"## {market.upper()} Market News\n\n"
        for i, r in enumerate(results, 1):
            date = r.get("date", "")[:10]
            title = r.get("title", "No title")
            body = r.get("body", "")[:180]
            source = r.get("source", "")
            url = r.get("url", "")
            output += f"**{i}. [{title}]({url})**\n"
            output += f"   *{source} — {date}*\n"
            output += f"   {body}...\n\n"

        return output
    except Exception as e:
        return f"Error fetching market news: {e}"
