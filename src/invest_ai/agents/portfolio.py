"""
Portfolio Analyst Agent — reviews the overall asset allocation, equity concentrations, and risk exposure of the user's family portfolio.
"""
import re
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage
from ..config import OLLAMA_BASE_URL, MODEL_NAME, MODEL_TEMPERATURE


def _sanitize_markdown(text: str) -> str:
    """Strip/normalise HTML tags that LLMs sometimes emit inside Markdown tables."""
    # Replace <br>, <br/>, <br /> with a space (table cells) or a newline (elsewhere)
    text = re.sub(r'<br\s*/?>', '  \n', text, flags=re.IGNORECASE)
    # Strip <b>…</b> wrappers — keep the inner text
    text = re.sub(r'<b>(.*?)</b>', r'**\1**', text, flags=re.IGNORECASE | re.DOTALL)
    # Strip <i>…</i> / <em>…</em> — keep inner text
    text = re.sub(r'<(?:i|em)>(.*?)</(?:i|em)>', r'_\1_', text, flags=re.IGNORECASE | re.DOTALL)
    # Remove any remaining HTML tags completely
    text = re.sub(r'<[^>]+>', '', text)
    # Decode common HTML entities
    text = text.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&').replace('&nbsp;', ' ')
    return text

_PORTFOLIO_REVIEW_PROMPT = """You are an elite, fee-only wealth manager and portfolio strategist.
Your task is to provide a comprehensive, institution-grade portfolio review and risk audit based on the aggregated family portfolio data provided below.

Provide your review in clear markdown, structured as follows:

# 📋 Family Portfolio Audit & Strategic Review

## 1. Executive Summary
- Overall portfolio health assessment (Total Value: {total_value}, Cost: {total_cost}, Gain: {total_gain} | {gain_pct}).
- Key takeaways regarding allocation, risk level, and return efficiency.

## 2. Asset Allocation & Diversification Analysis
- Critique of the balance between liquid assets (Equities, Global Equities, Liquid Cash, Gold/Silver) and illiquid assets (Real Estate, Vehicle, EPF/Retirement, ESOPs).
- Assess if the cash buffer (Liquid) is adequate given the total size.
- Evaluate real estate and vehicle concentrations (currently {real_estate_pct}% and {vehicle_pct}% of total net worth). Is the portfolio too asset-heavy?

## 3. Equity Portfolio Risk & Concentration
- Analysis of the stock holdings: Cap-size distribution (Mega, Large, Mid, Small Cap).
- Evaluation of top stock concentration (the top holdings list). Are they over-exposed to any single stock or theme (e.g. tech, memory, industrial etc.)?
- Evaluate the split between Indian (NSE/BSE) and Global (US) equities (current split: {indian_equity_pct}% Indian / {global_equity_pct}% US of the equity portion).

## 4. Platform & Broker Risk
- Note the broker distribution (from the data provided). Explain the custody risks, currency risks (INR vs USD), and tax implications of international investing (US stock holdings).

## 5. Actionable Strategic Recommendations
- Offer 3-5 concrete steps to optimize this portfolio (e.g., rebalancing, tax-loss harvesting, sector diversification, liquid net worth goals).
- Provide guidance on managing volatility.

Data Provided:
----------------
- High-Level Totals:
  - Total Portfolio Value: {total_value}
  - Total Invested Cost: {total_cost}
  - Net Profit/Loss: {total_gain}
  - Net Return Percentage: {gain_pct}

- Asset Class Breakdown:
{asset_class_breakdown}

- Equity Cap-Size Allocation:
{cap_size_breakdown}

- Equity Broker Allocation:
{broker_breakdown}

- Top Stock Holdings:
{top_holdings_breakdown}

User specific requests/focus:
{user_query}

Write in a highly professional, objective, and analytical tone. Do not give direct legal advice, but give clear financial rationale based on modern portfolio theory.

CRITICAL FORMATTING CONSTRAINT: Do NOT output any HTML tags (such as <br>, <b>, <i>, <ul>, etc.) inside markdown tables or anywhere in the report. If you need line breaks in a table cell, use spaces or write the text in a single block; never insert raw <br> or <br/> tags. Keep all tables and descriptions in clean, standard Markdown only. Ensure any lists are formatted using standard Markdown hyphens (-) and not HTML list tags.
"""

def run_portfolio_review_agent(portfolio_summary: dict, user_query: str = "") -> str:
    """
    Calls the LLM to generate a comprehensive portfolio review.
    """
    llm = ChatOllama(
        model=MODEL_NAME,
        base_url=OLLAMA_BASE_URL,
        temperature=MODEL_TEMPERATURE,
    )
    
    # Format the breakdowns into text
    # 1. Asset class breakdown
    ac_lines = []
    for idx, row in portfolio_summary['asset_class_df'].iterrows():
        ac_lines.append(f"- {row['Asset Class']}: Market Value: {row['Market Value']:,.2f} INR (Allocation: {row['Allocation (%)']:.2f}%) | Cost: {row['Invested']:,.2f} INR | PnL: {row['Gain/Loss']:+,.2f} INR ({row['Gain/Loss %']:.2f}%)")
    asset_class_breakdown = "\n".join(ac_lines)
    
    # 2. Cap-size breakdown
    cap_lines = []
    for idx, row in portfolio_summary['category_df'].iterrows():
        cap_lines.append(f"- {row['Category']}: Market Value: {row['Market Value']:,.2f} INR (Allocation: {row['Allocation (%)']:.2f}%)")
    cap_size_breakdown = "\n".join(cap_lines)
    
    # 3. Broker breakdown
    broker_lines = []
    for idx, row in portfolio_summary['broker_df'].iterrows():
        broker_lines.append(f"- {row['Broker']}: Market Value: {row['Market Value']:,.2f} INR (Allocation: {row['Allocation (%)']:.2f}%)")
    broker_breakdown = "\n".join(broker_lines)
    
    # 4. Top stock holdings
    th_lines = []
    for idx, row in portfolio_summary['top_holdings_df'].iterrows():
        th_lines.append(f"- {row['Investment']} ({row['Asset Type']}): Market Value: {row['Market Value']:,.2f} INR | Allocation of Liquid: {row['Holding (%)']*100:.2f}% | Return: {row['Total Gain/Loss (%)']:.2f}%")
    top_holdings_breakdown = "\n".join(th_lines)
    
    # Calculate percentages
    real_estate_mv = portfolio_summary['asset_class_mv_map'].get('Real Estate', 0.0)
    vehicle_mv = portfolio_summary['asset_class_mv_map'].get('Vehicle', 0.0)
    total_mv = portfolio_summary['total_market_value']
    
    real_estate_pct = (real_estate_mv / total_mv * 100) if total_mv > 0 else 0.0
    vehicle_pct = (vehicle_mv / total_mv * 100) if total_mv > 0 else 0.0
    
    indian_eq_mv = portfolio_summary['asset_class_mv_map'].get('Equity', 0.0)
    global_eq_mv = portfolio_summary['asset_class_mv_map'].get('Global Equity', 0.0)
    total_eq_mv = indian_eq_mv + global_eq_mv
    
    indian_equity_pct = (indian_eq_mv / total_eq_mv * 100) if total_eq_mv > 0 else 0.0
    global_equity_pct = (global_eq_mv / total_eq_mv * 100) if total_eq_mv > 0 else 0.0
    
    # Format high-level numbers
    total_value_str = f"{total_mv:,.2f} INR"
    total_cost_str = f"{portfolio_summary['total_invested']:,.2f} INR"
    total_gain_str = f"{portfolio_summary['total_gain']:+,.2f} INR"
    gain_pct_str = f"{portfolio_summary['total_gain_pct']:.2f}%"
    
    prompt = _PORTFOLIO_REVIEW_PROMPT.format(
        total_value=total_value_str,
        total_cost=total_cost_str,
        total_gain=total_gain_str,
        gain_pct=gain_pct_str,
        asset_class_breakdown=asset_class_breakdown,
        cap_size_breakdown=cap_size_breakdown,
        broker_breakdown=broker_breakdown,
        top_holdings_breakdown=top_holdings_breakdown,
        real_estate_pct=f"{real_estate_pct:.1f}",
        vehicle_pct=f"{vehicle_pct:.1f}",
        indian_equity_pct=f"{indian_equity_pct:.1f}",
        global_equity_pct=f"{global_equity_pct:.1f}",
        user_query=user_query if user_query else "General Portfolio Health Assessment",
    )
    
    messages = [
        SystemMessage(content="You are a professional wealth advisor and investment strategist."),
        HumanMessage(content=prompt)
    ]
    
    try:
        response = llm.invoke(messages)
        return _sanitize_markdown(response.content.strip())
    except Exception as e:
        return f"Portfolio review agent failed: {e}"
