"""
Dividend analyst agent node — analyzes dividend safety, yield, and payout ratio.
"""
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent
from ..config import OLLAMA_BASE_URL, MODEL_NAME, MODEL_TEMPERATURE
from ..tools import FUNDAMENTAL_TOOLS
from .state import ResearchState

_DIVIDEND_PROMPT = """You are an expert dividend investing analyst.
Analyze the provided stock's dividend profile.

Use the available tools (especially get_dividends, get_cash_flow, get_income_statement) to gather data and provide a comprehensive dividend analysis including:
1. Current dividend yield and payout ratio
2. Dividend safety (is the dividend well-covered by free cash flow and earnings?)
3. Dividend growth history (are they consistently raising it?)
4. Overall dividend rating (Very Safe / Safe / Borderline / Unsafe)

Be specific with numbers. Highlight whether this is a good income investment."""


def dividend_node(state: ResearchState) -> dict:
    """Run dividend analysis on the stock."""
    ticker = state["ticker"]
    query = state.get("query", f"Provide full dividend analysis for {ticker}")

    llm = ChatOllama(
        model=MODEL_NAME,
        base_url=OLLAMA_BASE_URL,
        temperature=MODEL_TEMPERATURE,
    )

    agent = create_react_agent(llm, FUNDAMENTAL_TOOLS, prompt=_DIVIDEND_PROMPT)

    try:
        result = agent.invoke({
            "messages": [HumanMessage(content=f"Analyze {ticker} dividends. {query}")]
        })
        analysis = result["messages"][-1].content
    except Exception as e:
        analysis = f"Dividend analysis failed: {e}"

    return {"dividend_analysis": analysis, "agents_called": ["dividend"]}
