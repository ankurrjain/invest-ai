"""
Comparison agent node — compares multiple stocks side by side.
"""
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent
from ..config import OLLAMA_BASE_URL, MODEL_NAME, MODEL_TEMPERATURE
from ..tools import ALL_TOOLS
from .state import ResearchState

_COMPARISON_PROMPT = """You are an expert investment analyst specializing in comparative stock analysis.
You have been provided with a list of tickers to compare.

Use the available tools (especially compare_stocks) to gather data and provide a comprehensive comparison report including:
1. Side-by-side valuation comparison (P/E, EV/EBITDA, etc.)
2. Performance comparison (Price returns, historical data)
3. Financial health & profitability comparison
4. A clear recommendation on which stock represents the better investment opportunity right now, and why.

Structure the report clearly with markdown tables where appropriate."""


def comparison_node(state: ResearchState) -> dict:
    """Run comparison analysis on multiple stocks."""
    tickers = state["ticker"] # This is expected to be a comma-separated string
    query = state.get("query", f"Compare these stocks: {tickers}")

    llm = ChatOllama(
        model=MODEL_NAME,
        base_url=OLLAMA_BASE_URL,
        temperature=MODEL_TEMPERATURE,
    )

    agent = create_react_agent(llm, ALL_TOOLS, prompt=_COMPARISON_PROMPT)

    try:
        result = agent.invoke({
            "messages": [HumanMessage(content=f"Compare the following stocks: {tickers}. {query}")]
        })
        analysis = result["messages"][-1].content
    except Exception as e:
        analysis = f"Comparison analysis failed: {e}"

    return {"comparison_analysis": analysis, "agents_called": ["comparison"]}
