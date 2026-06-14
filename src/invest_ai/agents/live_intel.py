"""
Live Intelligence agent node — gathers real-time data about a company:
earnings history, analyst estimates, upcoming catalysts, insider activity,
institutional changes, and company operations intelligence.
"""
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent
from ..config import OLLAMA_BASE_URL, MODEL_NAME, MODEL_TEMPERATURE
from ..tools import LIVE_INTEL_TOOLS
from .state import ResearchState

_LIVE_INTEL_PROMPT = """You are a senior live intelligence analyst specializing in real-time company research.
Your mission is to gather the most current, factual data about a company from live sources and produce
a comprehensive intelligence dossier.

Use ALL available tools to collect:
1. **Earnings History**: Run get_earnings_history — look at last 4 quarters of EPS & revenue vs estimates.
   Did the company consistently beat, miss, or match expectations? What's the trend?

2. **Analyst Estimates**: Run get_analyst_estimates — what is the current consensus rating?
   What are analyst price targets? Are estimates being revised up or down?

3. **Upcoming Catalysts**: Run get_upcoming_catalysts — when is the next earnings date?
   What events, product launches, partnerships, or regulatory decisions are coming?

4. **Insider Activity**: Run get_insider_activity — are insiders buying or selling?
   Large insider buys are bullish signals; heavy selling can be a red flag.

5. **Institutional Changes**: Run get_institutional_changes — who are the top holders?
   Are institutional investors increasing or reducing positions?

6. **Company Operations**: Run search_company_operations — understand the company's global footprint,
   recent strategic moves, market position, and competitive landscape.

After gathering all data, synthesize your findings and produce a well-structured live intelligence report.
Be factual and data-driven. Use the actual numbers from the tools.
Focus especially on: "Based on all this live data, is the company likely to beat or miss its next earnings?"
Consider the beat/miss history, analyst estimate trends, insider behavior, and catalysts."""


def live_intel_node(state: ResearchState) -> dict:
    """Run live intelligence analysis — gathers real-time internet data about the stock."""
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

    agent = create_react_agent(llm, LIVE_INTEL_TOOLS, prompt=_LIVE_INTEL_PROMPT)

    prompt = (
        f"Run a complete live intelligence analysis for {company} (ticker: {ticker}).\n"
        f"Use ALL the available tools to gather: earnings history, analyst estimates, "
        f"upcoming catalysts, insider activity, institutional changes, and company operations.\n"
        f"After collecting all data, write a comprehensive live intelligence report with a clear verdict "
        f"on whether the company is likely to beat or miss its next earnings results.\n"
        f"Additional user context: {query}"
    )

    try:
        result = agent.invoke({"messages": [HumanMessage(content=prompt)]})
        analysis = result["messages"][-1].content
    except Exception as e:
        analysis = f"Live intelligence analysis failed: {e}"

    return {
        "live_intel_analysis": analysis,
        "agents_called": ["live_intel"],
        "company_name": company_name,
        "current_price": current_price,
    }
