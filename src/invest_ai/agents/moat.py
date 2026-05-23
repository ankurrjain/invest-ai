"""
Economic moat analyst agent node — analyzes competitive advantages, ROIC, and margins.
"""
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent
from ..config import OLLAMA_BASE_URL, MODEL_NAME, MODEL_TEMPERATURE
from ..tools import FUNDAMENTAL_TOOLS, NEWS_TOOLS
from .state import ResearchState

_MOAT_PROMPT = """You are an expert equity analyst specializing in identifying Economic Moats (durable competitive advantages).
Analyze the provided stock to determine if it has a moat.

Use the available fundamental and news tools to gather data and provide a comprehensive moat analysis including:
1. Identified Competitive Advantages (Network effects, Switching costs, Intangible assets, Cost advantage, Efficient scale)
2. Evidence of Moat: Consistently high Return on Invested Capital (ROIC) or High Profit Margins
3. Moat Trend (Is the competitive advantage widening, stable, or narrowing?)
4. Overall Moat Rating (Wide / Narrow / None)

Be specific with numbers and examples. Highlight what makes this business difficult to disrupt."""


def moat_node(state: ResearchState) -> dict:
    """Run moat analysis on the stock."""
    ticker = state["ticker"]
    query = state.get("query", f"Provide full economic moat analysis for {ticker}")

    llm = ChatOllama(
        model=MODEL_NAME,
        base_url=OLLAMA_BASE_URL,
        temperature=MODEL_TEMPERATURE,
    )

    tools = FUNDAMENTAL_TOOLS + NEWS_TOOLS
    agent = create_react_agent(llm, tools, prompt=_MOAT_PROMPT)

    try:
        result = agent.invoke({
            "messages": [HumanMessage(content=f"Analyze {ticker}'s economic moat. {query}")]
        })
        analysis = result["messages"][-1].content
    except Exception as e:
        analysis = f"Moat analysis failed: {e}"

    return {"moat_analysis": analysis, "agents_called": ["moat"]}
