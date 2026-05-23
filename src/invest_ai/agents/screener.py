"""
Thematic screener agent node — searches for stocks based on a theme and filters them based on technicals and moat.
"""
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent
from ..config import OLLAMA_BASE_URL, MODEL_NAME, MODEL_TEMPERATURE
from ..tools import ALL_TOOLS
from .state import ResearchState

_SCREENER_PROMPT = """You are an expert thematic stock screener and equity analyst.
You have been given an investment theme. Your job is to identify the best stocks to invest in within this theme.

Use the available search and financial tools to:
1. Identify 3-5 relevant stocks that strongly fit the theme.
2. For each identified stock, briefly evaluate its Economic Moat (competitive advantages, margins).
3. For each identified stock, briefly evaluate its Technical setup (is it a good time to enter?).
4. Provide a final summarized list of your top picks within the theme, ranking them by attractiveness.

Make sure to look up the actual ticker symbols for the companies you identify before using the financial tools."""


def screener_node(state: ResearchState) -> dict:
    """Run thematic screener on a given theme."""
    theme = state["ticker"] # In screener mode, the 'ticker' field holds the theme query string
    query = state.get("query", f"Find stocks matching this theme: {theme}")

    llm = ChatOllama(
        model=MODEL_NAME,
        base_url=OLLAMA_BASE_URL,
        temperature=MODEL_TEMPERATURE,
    )

    agent = create_react_agent(llm, ALL_TOOLS, prompt=_SCREENER_PROMPT)

    try:
        result = agent.invoke({
            "messages": [HumanMessage(content=f"Screen for stocks matching the theme: '{theme}'. {query}")]
        })
        analysis = result["messages"][-1].content
    except Exception as e:
        analysis = f"Screener analysis failed: {e}"

    return {"screener_analysis": analysis, "agents_called": ["screener"]}
