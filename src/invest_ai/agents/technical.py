"""
Technical analyst agent node — runs technical analysis tools and returns findings.
"""
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.prebuilt import create_react_agent
from ..config import OLLAMA_BASE_URL, MODEL_NAME, MODEL_TEMPERATURE
from ..tools import TECHNICAL_TOOLS
from .state import ResearchState

_TECHNICAL_PROMPT = """You are an expert technical analyst specializing in stock market analysis.
Analyze the provided stock using technical indicators.

Use the available tools to gather data and then provide a comprehensive technical analysis including:
1. Current price action and trend direction
2. Key support and resistance levels from moving averages
3. Momentum signals (RSI, MACD)
4. Volatility assessment (Bollinger Bands)
5. Volume analysis
6. Overall technical rating (Bullish / Neutral / Bearish) with confidence level
7. Key price levels to watch

Be specific with numbers. Format your analysis clearly with sections."""


def technical_node(state: ResearchState) -> dict:
    """Run technical analysis on the stock."""
    ticker = state["ticker"]
    query = state.get("query", f"Provide full technical analysis for {ticker}")

    llm = ChatOllama(
        model=MODEL_NAME,
        base_url=OLLAMA_BASE_URL,
        temperature=MODEL_TEMPERATURE,
    )

    agent = create_react_agent(llm, TECHNICAL_TOOLS, prompt=_TECHNICAL_PROMPT)

    try:
        result = agent.invoke({
            "messages": [HumanMessage(content=f"Analyze {ticker} technically. {query}")]
        })
        # Extract the last AI message
        analysis = result["messages"][-1].content
    except Exception as e:
        analysis = f"Technical analysis failed: {e}"

    return {"technical_analysis": analysis, "agents_called": ["technical"]}
