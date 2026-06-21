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


def run_dividend_planner_agent(
    candidates_df, 
    num_stocks: int, 
    target_income: float, 
    frequency: str, 
    market: str, 
    preferences: str = ""
) -> tuple[list[str], str]:
    """
    Invokes the ChatOllama LLM to select exactly num_stocks from candidates_df.
    Returns:
        (selected_tickers_list, explanation_markdown)
    """
    from langchain_core.messages import SystemMessage, HumanMessage
    import json
    import re
    
    currency = "₹" if market == "india" else "$"
    
    # Format candidates list for the agent
    candidates_list = []
    for idx, row in candidates_df.iterrows():
        candidates_list.append(
            f"- {row['Symbol']}: {row['Name']} | Price: {currency}{row['Price']} | Yield: {row['Yield (%)']}% | Payout Ratio: {row['Payout Ratio (%)']}% | Sector: {row['Sector']}"
        )
    candidates_str = "\n".join(candidates_list)
    
    prompt = f"""You are an expert dividend portfolio architect.
Your task is to select the best {num_stocks} stocks from the candidate list below for a dividend growth portfolio.

The user's goal is:
- Target income: {target_income} {currency} per {frequency}
- Market: {market.upper()}
- Preferences/Constraints: {preferences if preferences else "None"}

Candidate Pool:
{candidates_str}

Please select exactly {num_stocks} stocks.
Prioritize:
1. High and sustainable dividend yields.
2. Reasonable payout ratios (typically under 80% is safer, but utilities/REITs can be higher; for Indian PSUs, payout ratios can be higher but backed by govt/monopolistic earnings).
3. Sector diversification (do not put all selected stocks in one sector).
4. Stable business models with potential for future dividend growth.

Your response MUST be in two parts:
1. A JSON list of the selected ticker symbols at the very beginning of your response, inside a code block tagged with 'json'. Example:
```json
[
  "TICKER1",
  "TICKER2"
]
```
2. A detailed markdown analysis explaining:
   - Why you chose this particular set of stocks.
   - Sector distribution and risk assessment.
   - Key highlights for each selected stock (yield, payout ratio, safety).
   - Advice on building and managing this dividend income stream.
"""

    llm = ChatOllama(
        model=MODEL_NAME,
        base_url=OLLAMA_BASE_URL,
        temperature=MODEL_TEMPERATURE,
    )
    
    messages = [
        SystemMessage(content="You are a professional equity research and dividend portfolio specialist."),
        HumanMessage(content=prompt)
    ]
    
    selected_tickers = []
    explanation = ""
    try:
        response = llm.invoke(messages)
        content = response.content.strip()
        explanation = content
        
        # Try to extract JSON code block
        match = re.search(r"```json\s*(.*?)\s*```", content, re.DOTALL)
        if match:
            tickers = json.loads(match.group(1))
            if isinstance(tickers, list):
                selected_tickers = [t.strip().upper() for t in tickers]
        else:
            # Fallback regex search for anything that looks like JSON list
            match_list = re.search(r"\[\s*\"[A-Z0-9.\-]+\"(?:\s*,\s*\"[A-Z0-9.\-]+\")*\s*\]", content)
            if match_list:
                tickers = json.loads(match_list.group(0))
                selected_tickers = [t.strip().upper() for t in tickers]
    except Exception as e:
        explanation = f"Agent selection failed: {e}\nFalling back to top dividend yield stocks."
        
    # Clean selected tickers to make sure they are in the candidates list
    valid_symbols = set(candidates_df["Symbol"].tolist())
    selected_tickers = [t for t in selected_tickers if t in valid_symbols]
    
    # Fallback to top N by yield if selection is empty or less than expected
    if len(selected_tickers) < num_stocks:
        top_yields = candidates_df.head(num_stocks)["Symbol"].tolist()
        for t in top_yields:
            if t not in selected_tickers:
                selected_tickers.append(t)
        selected_tickers = selected_tickers[:num_stocks]
        
    return selected_tickers, explanation

