"""
Supervisor agent — decides which specialist agents to invoke based on the user's query.
"""
import json
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage
from ..config import OLLAMA_BASE_URL, MODEL_NAME, MODEL_TEMPERATURE
from .state import ResearchState

_SUPERVISOR_PROMPT = """You are the research supervisor for a stock analysis platform.

Given a user's query about a stock, decide which specialist agents to call:
- "technical"     — for price action, RSI, MACD, moving averages, chart patterns
- "fundamental"   — for P/E, earnings, revenue, balance sheet, valuation
- "news"          — for recent news, events, sentiment, catalysts
- "dividend"      — for dividend yield, safety, payout ratio, growth
- "moat"          — for economic moat, competitive advantage, ROIC

Respond ONLY with valid JSON in this format:
{{"agents": ["technical", "fundamental", "news"], "reason": "brief explanation"}}

You may select any combination of agents depending on what the query needs.
Always include "news" if the query asks about recent events, outlook, or market sentiment.
Always include "technical" if asking about price, chart, buy/sell signals.
Always include "fundamental" if asking about company value, earnings, financials.
Include "dividend" if the query asks about dividends or income.
Include "moat" if the query asks about competitive advantage or moat.
For a full research / deep dive, include ["technical", "fundamental", "news"]."""


def supervisor_node(state: ResearchState) -> dict:
    """Route the query to the appropriate specialist agents."""
    mode = state.get("mode", "single")
    if mode not in ("single",):
        # For compare, screener, live_intel, live_news — enrich company info and pass through
        company_name = state.get("company_name")
        current_price = state.get("current_price")
        if not company_name and mode not in ("screener",):
            try:
                import yfinance as yf
                ticker = state.get("ticker", "")
                info = yf.Ticker(ticker).info
                company_name = info.get("longName", ticker)
                current_price = info.get("currentPrice") or info.get("regularMarketPrice")
            except Exception:
                pass
        return {"agents_to_call": [], "agents_called": [], "company_name": company_name, "current_price": current_price}

    llm = ChatOllama(
        model=MODEL_NAME,
        base_url=OLLAMA_BASE_URL,
        temperature=MODEL_TEMPERATURE,
    )

    query = state.get("query", "")
    ticker = state.get("ticker", "")
    market = state.get("market", "us")

    messages = [
        SystemMessage(content=_SUPERVISOR_PROMPT),
        HumanMessage(content=f"Stock: {ticker} (Market: {market})\nQuery: {query}"),
    ]

    try:
        response = llm.invoke(messages)
        content = response.content.strip()
        # Extract JSON from response (handle markdown fences)
        if "```" in content:
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        parsed = json.loads(content)
        agents = parsed.get("agents", ["technical", "fundamental", "news"])
    except Exception:
        # Fallback: call core three
        agents = ["technical", "fundamental", "news"]

    # Enrich with company name and price upfront
    company_name = None
    current_price = None
    try:
        import yfinance as yf
        info = yf.Ticker(ticker).info
        company_name = info.get("longName", ticker)
        current_price = info.get("currentPrice") or info.get("regularMarketPrice")
    except Exception:
        pass

    return {
        "agents_to_call": agents,
        "agents_called": [],
        "company_name": company_name,
        "current_price": current_price,
    }
