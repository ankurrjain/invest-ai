"""
News and sentiment agent node.
"""
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent
from ..config import OLLAMA_BASE_URL, MODEL_NAME, MODEL_TEMPERATURE
from ..tools import NEWS_TOOLS
from .state import ResearchState

_NEWS_PROMPT = """You are an expert financial news analyst and sentiment specialist.
Analyze recent news and market sentiment for the provided stock.

Use the search tools to find recent news, then provide:
1. Summary of the most important recent news (last 1-2 weeks)
2. Overall sentiment assessment (Bullish / Neutral / Bearish)
3. Key catalysts (positive and negative)
4. Any upcoming events (earnings, product launches, regulatory decisions)
5. Market/sector tailwinds or headwinds
6. How the news might impact the stock price

Be concise but insightful. Focus on what actually matters for investors."""


def news_node(state: ResearchState) -> dict:
    """Run news and sentiment analysis on the stock."""
    ticker = state["ticker"]
    company = state.get("company_name") or ticker
    query = state.get("query", "")

    llm = ChatOllama(
        model=MODEL_NAME,
        base_url=OLLAMA_BASE_URL,
        temperature=MODEL_TEMPERATURE,
    )

    agent = create_react_agent(llm, NEWS_TOOLS, prompt=_NEWS_PROMPT)

    prompt = f"Search for and analyze recent news about {company} ({ticker}). {query}"
    try:
        result = agent.invoke({"messages": [HumanMessage(content=prompt)]})
        analysis = result["messages"][-1].content
    except Exception as e:
        analysis = f"News analysis failed: {e}"

    return {"news_analysis": analysis, "agents_called": ["news"]}
