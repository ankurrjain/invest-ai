"""
Fundamental analysis tools using yfinance — valuation, financials, balance sheet, dividends.
"""
import yfinance as yf
import pandas as pd
from langchain_core.tools import tool
from ..utils.formatters import format_number, format_pct, safe_get
from ..utils.ticker import get_currency_symbol


@tool
def get_valuation_metrics(ticker: str) -> str:
    """Get key valuation ratios: P/E, P/B, P/S, EV/EBITDA, PEG, EPS and growth rates."""
    try:
        info = yf.Ticker(ticker).info
        cur = get_currency_symbol(ticker)

        eg = info.get("earningsGrowth")
        rg = info.get("revenueGrowth")
        pm = info.get("profitMargins")
        om = info.get("operatingMargins")

        return f"""## Valuation Metrics — {ticker}

| Metric | Value |
|--------|-------|
| P/E (TTM) | {format_number(info.get('trailingPE'))}x |
| Forward P/E | {format_number(info.get('forwardPE'))}x |
| PEG Ratio | {format_number(info.get('pegRatio'))} |
| Price/Book | {format_number(info.get('priceToBook'))}x |
| Price/Sales | {format_number(info.get('priceToSalesTrailing12Months'))}x |
| EV/EBITDA | {format_number(info.get('enterpriseToEbitda'))}x |
| EV/Revenue | {format_number(info.get('enterpriseToRevenue'))}x |

| Earnings | Value |
|----------|-------|
| EPS (TTM) | {cur}{format_number(info.get('trailingEps'), 2)} |
| Forward EPS | {cur}{format_number(info.get('forwardEps'), 2)} |
| Earnings Growth | {format_pct(eg) if eg else 'N/A'} |
| Revenue Growth | {format_pct(rg) if rg else 'N/A'} |
| Profit Margin | {format_pct(pm) if pm else 'N/A'} |
| Operating Margin | {format_pct(om) if om else 'N/A'} |
"""
    except Exception as e:
        return f"Error fetching valuation metrics for {ticker}: {e}"


@tool
def get_income_statement(ticker: str) -> str:
    """Get income statement: revenue, gross profit, operating income, net income (annual, last 3 years)."""
    try:
        stock = yf.Ticker(ticker)
        cur = get_currency_symbol(ticker)
        financials = stock.financials

        if financials is None or financials.empty:
            return f"No income statement data for {ticker}"

        rows_wanted = ["Total Revenue", "Gross Profit", "Operating Income", "Net Income",
                       "EBITDA", "Basic EPS"]
        available = [r for r in rows_wanted if r in financials.index]
        df = financials.loc[available].iloc[:, :3]
        df.columns = [c.strftime("%Y") if hasattr(c, "strftime") else str(c) for c in df.columns]

        formatted = df.map(lambda x: format_number(x, 2, prefix=cur) if pd.notnull(x) else "N/A")

        return f"""## Income Statement — {ticker}
{formatted.to_markdown()}
"""
    except Exception as e:
        return f"Error fetching income statement for {ticker}: {e}"


@tool
def get_balance_sheet(ticker: str) -> str:
    """Get balance sheet: total assets, liabilities, equity, cash, and debt (last 3 years)."""
    try:
        stock = yf.Ticker(ticker)
        cur = get_currency_symbol(ticker)
        bs = stock.balance_sheet

        if bs is None or bs.empty:
            return f"No balance sheet data for {ticker}"

        rows_wanted = ["Total Assets", "Total Liabilities Net Minority Interest",
                       "Stockholders Equity", "Cash And Cash Equivalents",
                       "Total Debt", "Net Debt", "Working Capital"]
        available = [r for r in rows_wanted if r in bs.index]
        df = bs.loc[available].iloc[:, :3]
        df.columns = [c.strftime("%Y") if hasattr(c, "strftime") else str(c) for c in df.columns]
        formatted = df.map(lambda x: format_number(x, 2, prefix=cur) if pd.notnull(x) else "N/A")

        return f"""## Balance Sheet — {ticker}
{formatted.to_markdown()}
"""
    except Exception as e:
        return f"Error fetching balance sheet for {ticker}: {e}"


@tool
def get_cash_flow(ticker: str) -> str:
    """Get cash flow statement: operating, investing, financing, and free cash flow."""
    try:
        stock = yf.Ticker(ticker)
        cur = get_currency_symbol(ticker)
        cf = stock.cashflow

        if cf is None or cf.empty:
            return f"No cash flow data for {ticker}"

        rows_wanted = ["Operating Cash Flow", "Investing Cash Flow",
                       "Financing Cash Flow", "Free Cash Flow",
                       "Capital Expenditure", "Repurchase Of Capital Stock"]
        available = [r for r in rows_wanted if r in cf.index]
        df = cf.loc[available].iloc[:, :3]
        df.columns = [c.strftime("%Y") if hasattr(c, "strftime") else str(c) for c in df.columns]
        formatted = df.map(lambda x: format_number(x, 2, prefix=cur) if pd.notnull(x) else "N/A")

        return f"""## Cash Flow — {ticker}
{formatted.to_markdown()}
"""
    except Exception as e:
        return f"Error fetching cash flow for {ticker}: {e}"


@tool
def get_dividends(ticker: str) -> str:
    """Get dividend yield, payout ratio, and recent dividend history."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        cur = get_currency_symbol(ticker)

        dy = info.get("dividendYield")
        pr = info.get("payoutRatio")
        dps = info.get("dividendRate")
        ex_div = info.get("exDividendDate")

        result = f"""## Dividends — {ticker}
- **Dividend Yield:** {format_pct(dy) if dy else 'N/A'}
- **Annual Dividend/Share:** {cur}{format_number(dps, 2) if dps else 'N/A'}
- **Payout Ratio:** {format_pct(pr) if pr else 'N/A'}
- **Ex-Dividend Date:** {str(ex_div)[:10] if ex_div else 'N/A'}
"""
        try:
            hist_div = stock.dividends
            if hist_div is not None and not hist_div.empty:
                result += "\n**Recent Dividends (last 5):**\n"
                result += hist_div.tail(5).to_string()
        except Exception:
            pass
        return result
    except Exception as e:
        return f"Error fetching dividends for {ticker}: {e}"
