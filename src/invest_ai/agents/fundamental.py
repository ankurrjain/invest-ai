"""
Fundamental analyst agent node — runs fundamental analysis tools and returns findings.
"""
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent
from ..config import OLLAMA_BASE_URL, MODEL_NAME, MODEL_TEMPERATURE
from ..tools import FUNDAMENTAL_TOOLS
from .state import ResearchState

_FUNDAMENTAL_PROMPT = """You are an expert fundamental analyst with deep knowledge of financial statements.
Analyze the provided stock from a fundamental perspective.

Use the available tools to gather data and provide a comprehensive fundamental analysis including:
1. Business overview and competitive position
2. Valuation assessment (is it cheap or expensive vs peers/history?)
3. Revenue and earnings growth trends
4. Balance sheet health (debt levels, cash position)
5. Profitability metrics (margins, ROE, ROA)
6. Dividend profile (if applicable)
7. Analyst consensus and price targets
8. Key risks and opportunities
9. Overall fundamental rating (Strong Buy / Buy / Hold / Sell / Strong Sell)

Be specific with numbers and ratios. Highlight what makes this stock attractive or concerning."""


def fundamental_node(state: ResearchState) -> dict:
    """Run fundamental analysis on the stock."""
    ticker = state["ticker"]
    query = state.get("query", f"Provide full fundamental analysis for {ticker}")

    llm = ChatOllama(
        model=MODEL_NAME,
        base_url=OLLAMA_BASE_URL,
        temperature=MODEL_TEMPERATURE,
    )

    agent = create_react_agent(llm, FUNDAMENTAL_TOOLS, prompt=_FUNDAMENTAL_PROMPT)

    try:
        result = agent.invoke({
            "messages": [HumanMessage(content=f"Analyze {ticker} fundamentally. {query}")]
        })
        analysis = result["messages"][-1].content
    except Exception as e:
        analysis = f"Fundamental analysis failed: {e}"

    return {"fundamental_analysis": analysis, "agents_called": ["fundamental"]}
