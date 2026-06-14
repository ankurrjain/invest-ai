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


_LIVE_INTEL_SYNTHESIZER_PROMPT = """You are a senior investment intelligence analyst.
You have been provided with comprehensive live intelligence data gathered from real-time sources.

Your task: Synthesize this data into a polished, professional Live Intelligence Report.

Structure your report EXACTLY as follows:

# {company} ({ticker}) — Live Intelligence Report
*Generated: {timestamp} | Market: {market}*

## Live Verdict
State clearly: LIKELY TO BEAT / LIKELY TO MISS / LIKELY IN-LINE with next earnings expectations.
Provide your confidence level (High / Medium / Low) and a 2-3 sentence rationale backed by the data.

## Earnings Track Record (Last 4 Quarters)
Summarize the beat/miss history. Is there a consistent pattern? What was the average surprise %?

## Analyst Consensus & Price Targets
Summarize the analyst consensus rating, price targets, and any recent estimate revisions.
Note if estimates are trending up (bullish) or down (bearish).

## Upcoming Events & Catalysts
List the next earnings date, any ex-dividend dates, and key upcoming events found in the research.

## Company Operations Intelligence
Summarize key facts about the company's operational footprint, employee count, key locations,
recent expansions, and strategic moves.

## Insider & Institutional Signals
Are insiders buying or selling? What are major institutions doing with their positions?
Interpret this as a signal (bullish/neutral/bearish).

## Risk Factors
Bullet list of the 4-5 most important risks that could cause a miss or negative surprise.

## Conclusion
A final 2-3 paragraph synthesis: what the data tells us overall, what to watch for, and the investment implication.

---
*Disclaimer: This is AI-generated research for informational purposes only. Not financial advice.*

Be professional, specific, and data-driven. Reference actual numbers from the intelligence data provided."""

_LIVE_NEWS_SYNTHESIZER_PROMPT = """You are a senior live news intelligence analyst.
You have been provided with comprehensive live news and sentiment data gathered from real-time sources.

Your task: Synthesize this data into a polished, professional Live News Report.

Structure your report EXACTLY as follows:

# {company} ({ticker}) — Live News Report
*Generated: {timestamp} | Market: {market}*

## Live News Verdict
State clearly: LIKELY TO OUTPERFORM / LIKELY TO UNDERPERFORM / LIKELY TO TRADE IN-LINE based on recent news and sentiment.
Provide your confidence level (High / Medium / Low) and a 2-3 sentence rationale backed by the news data.

## Breaking News Summary (Last 24-48 Hours)
Summarize the most important recent news events. What are the key headlines and developments?
Include timestamps and source credibility where available.

## Sentiment Analysis & Market Reaction
What is the overall sentiment (Bullish / Bearish / Neutral) and how has the market reacted?
Note any sentiment shifts or changes in tone from recent news.

## News-Driven Catalysts & Events
Identify specific news items that could act as catalysts for stock movement.
Include events like product announcements, partnerships, regulatory decisions, management changes, etc.

## Trending Topics & Social Signals
What are people talking about regarding this company right now?
Note any unusual volume of news or specific topics gaining traction.

## Live Event Impact Analysis
Analyze how current events might affect short-term price action (next 1-3 days).
Consider both opportunities and risks presented by the news flow.

## Risk Factors from News Flow
Bullet list of the 4-5 most important risks identified from recent news that could negatively impact the stock.

## Conclusion
A final 2-3 paragraph synthesis: what the news tells us overall, what to watch for in the coming days, and the short-term trading implications.

---
*Disclaimer: This is AI-generated research for informational purposes only. Not financial advice.*

Be professional, specific, and data-driven. Reference actual headlines, timestamps, and sources from the intelligence data provided."""


def synthesizer_node(state: ResearchState) -> dict:
    """Synthesize all analyst findings into a final report."""
    ticker = state.get("ticker", "")
    company = state.get("company_name") or ticker
    query = state.get("query", "")
    market = state.get("market", "us").upper()

    technical = state.get("technical_analysis", "")
    fundamental = state.get("fundamental_analysis", "")
    news = state.get("news_analysis", "")
    dividend = state.get("dividend_analysis", "")
    moat = state.get("moat_analysis", "")
    comparison = state.get("comparison_analysis", "")
    screener = state.get("screener_analysis", "")
    live_intel = state.get("live_intel_analysis", "")

    # If it's compare or screener mode, the specialist just generates the final report directly!
    mode = state.get("mode", "single")
    if mode == "compare" and comparison:
        return {"final_report": comparison}
    if mode == "screener" and screener:
        return {"final_report": screener}

    # Live Intel mode — use the specialized prompt
    if mode == "live_intel" and live_intel:
        from datetime import datetime
        timestamp = datetime.now().strftime("%B %d, %Y at %H:%M")

        llm = ChatOllama(
            model=MODEL_NAME,
            base_url=OLLAMA_BASE_URL,
            temperature=0.2,
        )

        prompt = f"""Company: {company} ({ticker})
Market: {market}
User Query: {query}

=== LIVE INTELLIGENCE DATA ===
{live_intel}

Please write the comprehensive Live Intelligence Report now, following the exact structure from your instructions.
Focus your verdict on whether the company is likely to beat, miss, or be in-line with next earnings."""

        messages = [
            SystemMessage(content=_LIVE_INTEL_SYNTHESIZER_PROMPT.format(
                company=company, ticker=ticker, timestamp=timestamp, market=market
            )),
            HumanMessage(content=prompt),
        ]

        try:
            response = llm.invoke(messages)
            report = response.content
        except Exception as e:
            # Fallback: return raw intelligence data if LLM synthesis fails
            report = f"# {company} ({ticker}) — Live Intelligence Report\n\n{live_intel}"

        return {"final_report": report}

    # Live News mode — use the specialized prompt
    if mode == "live_news" and live_news:
        from datetime import datetime
        timestamp = datetime.now().strftime("%B %d, %Y at %H:%M")

        llm = ChatOllama(
            model=MODEL_NAME,
            base_url=OLLAMA_BASE_URL,
            temperature=0.2,
        )

        prompt = f"""Company: {company} ({ticker})
Market: {market}
User Query: {query}

=== LIVE NEWS AND SENTIMENT DATA ===
{live_news}

Please write the comprehensive Live News Report now, following the exact structure from your instructions.
Focus your assessment on what breaking news or sentiment shifts are likely to impact the stock in the next 1-3 days."""

        messages = [
            SystemMessage(content=_LIVE_NEWS_SYNTHESIZER_PROMPT.format(
                company=company, ticker=ticker, timestamp=timestamp, market=market
            )),
            HumanMessage(content=prompt),
        ]

        try:
            response = llm.invoke(messages)
            report = response.content
        except Exception as e:
            # Fallback: return raw intelligence data if LLM synthesis fails
            report = f"# {company} ({ticker}) — Live News Report\n\n{live_news}"

        return {"final_report": report}

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
