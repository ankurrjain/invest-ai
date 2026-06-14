"""
Live News agent node — gathers real-time news and sentiment analysis.
"""
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent
from ..config import OLLAMA_BASE_URL, MODEL_NAME, MODEL_TEMPERATURE
from ..tools import NEWS_TOOLS
from .state import ResearchState

_LIVE_NEWS_PROMPT = """You are a live financial news intelligence specialist.
Your mission is to gather and analyze the most current, breaking news and sentiment about a company from live sources and produce
a real-time news report.

Use ALL available tools to collect:
1. **Breaking News**: Search for the latest news about the company (last 24-48 hours)
2. **Real-time Sentiment**: Gauge immediate market reaction to news events
3. **News-Driven Catalysts**: Identify specific news items that could move the stock price
4. **Trending Topics**: What are people talking about regarding this company right now?
5. **Live Event Impact**: Analyze how current events might affect short-term price action

After gathering all data, synthesize your findings and produce a well-structured live news intelligence report.
Be factual and data-driven. Use actual headlines, timestamps, and sources from the tools.
Focus especially on: "What breaking news or sentiment shifts are likely to impact the stock in the next 1-3 days?"
Consider the news volume, sentiment velocity, and credibility of sources."""
def live_news_node(state: ResearchState) -> dict:
    """Run live news and sentiment analysis — gathers real-time internet news about the stock."""
    ticker = state["ticker"]
    company = state.get("company_name") or ticker
    query = state.get("query", "")

    # Enrich with company name and current price if not already done
    company_name = state.get("company_name")
    current_price = state.get("current_price")
    if not company_name:
        try:
            import yfinance as yf
            info = yf.Ticker(ticker).info
            company_name = info.get("longName", ticker)
            current_price = info.get("currentPrice") or info.get("regularMarketPrice")
            company = company_name
        except Exception:
            pass

    llm = ChatOllama(
        model=MODEL_NAME,
        base_url=OLLAMA_BASE_URL,
        temperature=MODEL_TEMPERATURE,
    )

    agent = create_react_agent(llm, NEWS_TOOLS, prompt=_LIVE_NEWS_PROMPT)

    prompt = (
        f"Run a live news analysis for {company} (ticker: {ticker}).\n"
        f"Use ALL the available tools to gather: breaking news, real-time sentiment, "
        f"news-driven catalysts, trending topics, and live event impact.\n"
        f"After collecting all data, write a comprehensive live news report with a clear assessment "
        f"of what breaking news or sentiment shifts are likely to impact the stock in the next 1-3 days.\n"
        f"Additional user context: {query}"
    )

    try:
        result = agent.invoke({"messages": [HumanMessage(content=prompt)]})
        analysis = result["messages"][-1].content
    except Exception as e:
        analysis = f"Live news and sentiment analysis failed: {e}"

    return {
        "live_news_analysis": analysis,
        "agents_called": ["live_news"],
        "company_name": company_name,
        "current_price": current_price,
    }