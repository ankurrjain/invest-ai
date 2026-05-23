"""
Synthesizer agent — combines all specialist findings into a final investment research report.
"""
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage
from ..config import OLLAMA_BASE_URL, MODEL_NAME, MODEL_TEMPERATURE
from .state import ResearchState

_SYNTHESIZER_PROMPT = """You are a senior investment research analyst writing a professional research report.

Synthesize the findings from the specialist analysts into a comprehensive, well-structured investment report.

Structure your report as follows:

# {company} ({ticker}) — Investment Research Report

## Executive Summary
(2-3 sentences: what the stock is, overall verdict, key thesis)

## Investment Verdict
(Clear recommendation: Strong Buy / Buy / Hold / Sell / Strong Sell with target price range if possible)

## Technical Analysis Summary
(Summarize the key technical signals — trend, momentum, key levels)

## Fundamental Analysis Summary
(Summarize valuation, earnings quality, balance sheet health)

## News & Sentiment Summary
(Key recent events and market sentiment)

## Key Catalysts
(Bullet list: what could drive the stock up or down)

## Risk Factors
(Bullet list of main risks)

## Conclusion
(Final paragraph tying it together)

---
*Disclaimer: This is AI-generated research for informational purposes only. Not financial advice.*

Be professional, specific, and actionable. Use the actual data provided by the analysts."""


def synthesizer_node(state: ResearchState) -> dict:
    """Synthesize all analyst findings into a final report."""
    ticker = state.get("ticker", "")
    company = state.get("company_name") or ticker
    query = state.get("query", "")

    technical = state.get("technical_analysis", "")
    fundamental = state.get("fundamental_analysis", "")
    news = state.get("news_analysis", "")
    dividend = state.get("dividend_analysis", "")
    moat = state.get("moat_analysis", "")
    comparison = state.get("comparison_analysis", "")
    screener = state.get("screener_analysis", "")

    # If it's compare or screener mode, the specialist just generates the final report directly!
    mode = state.get("mode", "single")
    if mode == "compare" and comparison:
        return {"final_report": comparison}
    if mode == "screener" and screener:
        return {"final_report": screener}

    llm = ChatOllama(
        model=MODEL_NAME,
        base_url=OLLAMA_BASE_URL,
        temperature=0.2,
    )

    sections = []
    if technical:
        sections.append(f"=== TECHNICAL ANALYSIS ===\n{technical}")
    if fundamental:
        sections.append(f"=== FUNDAMENTAL ANALYSIS ===\n{fundamental}")
    if news:
        sections.append(f"=== NEWS & SENTIMENT ===\n{news}")
    if dividend:
        sections.append(f"=== DIVIDEND ANALYSIS ===\n{dividend}")
    if moat:
        sections.append(f"=== ECONOMIC MOAT ANALYSIS ===\n{moat}")

    analyst_findings = "\n\n".join(sections) if sections else "No specialist data available."

    prompt = f"""Company: {company} ({ticker})
User Query: {query}

Analyst Findings:
{analyst_findings}

Please write the comprehensive investment research report now."""

    messages = [
        SystemMessage(content=_SYNTHESIZER_PROMPT.format(company=company, ticker=ticker)),
        HumanMessage(content=prompt),
    ]

    try:
        response = llm.invoke(messages)
        report = response.content
    except Exception as e:
        report = f"Report generation failed: {e}"

    return {"final_report": report}
