"""
Live Intelligence tools — real-time earnings, analyst estimates, catalysts,
insider activity, institutional holdings, and company operations data.
All sources are free: yfinance + DuckDuckGo search.
"""
import yfinance as yf
import pandas as pd
from datetime import datetime, timezone
from langchain_core.tools import tool

try:
    from ddgs import DDGS
except ImportError:
    DDGS = None


# ─────────────────────────────────────────────────────────────────────────────
# Helper
# ─────────────────────────────────────────────────────────────────────────────

def _fmt(val, decimals: int = 2, suffix: str = "") -> str:
    """Format a number or return N/A."""
    if val is None or (isinstance(val, float) and (val != val)):
        return "N/A"
    try:
        return f"{float(val):,.{decimals}f}{suffix}"
    except Exception:
        return str(val)


def _pct(val) -> str:
    if val is None:
        return "N/A"
    try:
        return f"{float(val) * 100:+.2f}%"
    except Exception:
        return str(val)


# ─────────────────────────────────────────────────────────────────────────────
# Tool 1 — Earnings History
# ─────────────────────────────────────────────────────────────────────────────

@tool
def get_earnings_history(ticker: str) -> str:
    """
    Fetch the last 4 quarters of earnings history for a stock:
    EPS (actual vs estimated), revenue (actual vs estimated), and surprise %.
    Also returns the next earnings date if available.
    """
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        sections = [f"## Earnings History — {ticker}\n"]

        # --- Next Earnings Date ---
        next_date = info.get("earningsTimestamp") or info.get("earningsDate")
        if next_date:
            if isinstance(next_date, (int, float)):
                try:
                    dt = datetime.fromtimestamp(next_date, tz=timezone.utc)
                    sections.append(f"**Next Earnings Date:** {dt.strftime('%B %d, %Y')}\n")
                except Exception:
                    sections.append(f"**Next Earnings Date:** {next_date}\n")
            else:
                sections.append(f"**Next Earnings Date:** {next_date}\n")
        else:
            # Try earnings_dates df
            try:
                ed = stock.earnings_dates
                if ed is not None and not ed.empty:
                    future = ed[ed.index > pd.Timestamp.now(tz="UTC")]
                    if not future.empty:
                        sections.append(f"**Next Earnings Date:** {future.index[0].strftime('%B %d, %Y')}\n")
            except Exception:
                pass

        # --- EPS History (quarterly) ---
        try:
            eq = stock.quarterly_earnings
            if eq is not None and not eq.empty:
                sections.append("\n### EPS History (Quarterly)")
                sections.append("| Quarter | EPS Actual | EPS Estimate | Surprise % |")
                sections.append("|---------|-----------|--------------|------------|")
                for idx, row in eq.head(4).iterrows():
                    actual = _fmt(row.get("Reported EPS") or row.get("EPS Actual") or row.get("Actual"), 2)
                    estimate = _fmt(row.get("Estimated EPS") or row.get("EPS Estimate") or row.get("Estimate"), 2)
                    surprise = row.get("Surprise(%)") or row.get("Surprise %")
                    surprise_str = f"{float(surprise):+.2f}%" if surprise is not None else "N/A"
                    beat = "[BEAT]" if surprise and float(surprise) > 0 else ("[MISS]" if surprise and float(surprise) < 0 else "[IN-LINE]")
                    sections.append(f"| {idx} | {actual} | {estimate} | {surprise_str} {beat} |")
        except Exception:
            pass

        # Try earnings_dates for EPS estimates
        try:
            ed = stock.earnings_dates
            if ed is not None and not ed.empty:
                past = ed[ed.index <= pd.Timestamp.now(tz="UTC")].head(4)
                if not past.empty and "EPS Estimate" in past.columns:
                    sections.append("\n### EPS vs Estimate (from earnings_dates)")
                    sections.append("| Date | EPS Estimate | EPS Reported | Surprise % |")
                    sections.append("|------|-------------|--------------|------------|")
                    for idx, row in past.iterrows():
                        est = _fmt(row.get("EPS Estimate"), 2)
                        rep = _fmt(row.get("Reported EPS"), 2)
                        surp = row.get("Surprise(%)")
                        surp_str = f"{float(surp):+.2f}%" if surp is not None and str(surp) != "nan" else "N/A"
                        beat = ""
                        if surp is not None and str(surp) != "nan":
                            beat = "[BEAT]" if float(surp) > 0 else ("[MISS]" if float(surp) < 0 else "[IN-LINE]")
                        sections.append(f"| {idx.strftime('%b %Y')} | {est} | {rep} | {surp_str} {beat} |")
        except Exception:
            pass

        # --- Annual Net Income & Revenue (using income_stmt, not deprecated earnings) ---
        try:
            inc = stock.income_stmt
            if inc is not None and not inc.empty:
                sections.append("\n### Annual Net Income & Revenue")
                sections.append("| Year | Net Income | Total Revenue |")
                sections.append("|------|------------|---------------|")
                for col in list(inc.columns)[:4]:
                    year = col.strftime("%Y") if hasattr(col, "strftime") else str(col)[:4]
                    net_inc = inc.loc["Net Income", col] if "Net Income" in inc.index else None
                    tot_rev = inc.loc["Total Revenue", col] if "Total Revenue" in inc.index else None
                    net_str = f"{net_inc/1e9:.2f}B" if net_inc and str(net_inc) != "nan" else "N/A"
                    rev_str = f"{tot_rev/1e9:.2f}B" if tot_rev and str(tot_rev) != "nan" else "N/A"
                    sections.append(f"| {year} | {net_str} | {rev_str} |")
        except Exception:
            pass

        result = "\n".join(sections)
        if len(result.strip()) < 100:
            return f"## Earnings History — {ticker}\nLimited earnings history available via free API."
        return result

    except Exception as e:
        return f"Error fetching earnings history for {ticker}: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# Tool 2 — Analyst Estimates & Price Targets
# ─────────────────────────────────────────────────────────────────────────────

@tool
def get_analyst_estimates(ticker: str) -> str:
    """
    Get analyst consensus, price targets (mean/high/low), EPS/revenue forward
    estimates, and recent rating changes for a stock.
    """
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        sections = [f"## Analyst Estimates & Consensus — {ticker}\n"]

        # --- Recommendation ---
        rec = info.get("recommendationMean")
        rec_key = info.get("recommendationKey", "").replace("_", " ").title()
        n_analysts = info.get("numberOfAnalystOpinions")
        sections.append(f"**Consensus Rating:** {rec_key} (score: {_fmt(rec, 1)}/5, {n_analysts or 'N/A'} analysts)\n")

        # --- Price Targets ---
        target_mean = info.get("targetMeanPrice")
        target_high = info.get("targetHighPrice")
        target_low = info.get("targetLowPrice")
        current = info.get("currentPrice") or info.get("regularMarketPrice")
        sections.append("### Price Targets")
        sections.append(f"- **Current Price:** {_fmt(current, 2)}")
        sections.append(f"- **Mean Target:** {_fmt(target_mean, 2)}")
        sections.append(f"- **High Target:** {_fmt(target_high, 2)}")
        sections.append(f"- **Low Target:** {_fmt(target_low, 2)}")
        if current and target_mean:
            upside = (float(target_mean) - float(current)) / float(current) * 100
            sections.append(f"- **Implied Upside (Mean):** {upside:+.1f}%")

        # --- EPS Estimates ---
        try:
            eps_est = stock.eps_trend
            if eps_est is not None and not eps_est.empty:
                sections.append("\n### EPS Estimate Trend")
                sections.append(eps_est.to_markdown())
        except Exception:
            pass

        try:
            ee = stock.earnings_estimate
            if ee is not None and not ee.empty:
                sections.append("\n### Forward Earnings Estimates")
                sections.append(ee.to_markdown())
        except Exception:
            pass

        # --- Revenue Estimates ---
        try:
            re = stock.revenue_estimate
            if re is not None and not re.empty:
                sections.append("\n### Forward Revenue Estimates")
                sections.append(re.to_markdown())
        except Exception:
            pass

        # --- Analyst Rating Upgrades/Downgrades (last 10) ---
        try:
            ud = stock.upgrades_downgrades
            if ud is not None and not ud.empty:
                recent = ud.head(10)
                sections.append("\n### Recent Analyst Rating Changes (Last 10)")
                sections.append("| Date | Firm | From Grade | To Grade | Action |")
                sections.append("|------|------|-----------|---------|--------|")
                for idx, row in recent.iterrows():
                    date_str = idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx)[:10]
                    firm = row.get("Firm", "N/A")
                    from_g = row.get("FromGrade", "N/A")
                    to_g = row.get("ToGrade", "N/A")
                    action = row.get("Action", "N/A")
                    sections.append(f"| {date_str} | {firm} | {from_g} | {to_g} | {action} |")
        except Exception:
            pass

        # --- Recommendations Summary ---
        try:
            rs = stock.recommendations_summary
            if rs is not None and not rs.empty:
                sections.append("\n### Recommendations Summary")
                sections.append(rs.head(4).to_markdown())
        except Exception:
            pass

        return "\n".join(sections)

    except Exception as e:
        return f"Error fetching analyst estimates for {ticker}: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# Tool 3 — Upcoming Catalysts
# ─────────────────────────────────────────────────────────────────────────────

@tool
def get_upcoming_catalysts(ticker: str) -> str:
    """
    Identify upcoming catalysts for a stock: next earnings date, ex-dividend date,
    and search for recent news about product launches, regulatory decisions,
    analyst events, and other near-term catalysts.
    """
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        company = info.get("longName", ticker)
        sections = [f"## Upcoming Catalysts — {company} ({ticker})\n"]

        # --- Key Dates ---
        sections.append("### Key Dates")

        # Earnings
        try:
            ed = stock.earnings_dates
            if ed is not None and not ed.empty:
                future = ed[ed.index > pd.Timestamp.now(tz="UTC")]
                if not future.empty:
                    next_earn = future.index[0].strftime("%B %d, %Y")
                    sections.append(f"- **Next Earnings Date:** {next_earn}")
                else:
                    sections.append("- **Next Earnings Date:** Not yet announced")
            else:
                ts = info.get("earningsTimestamp")
                if ts:
                    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
                    sections.append(f"- **Next Earnings Date:** {dt.strftime('%B %d, %Y')}")
                else:
                    sections.append("- **Next Earnings Date:** N/A")
        except Exception:
            sections.append("- **Next Earnings Date:** N/A")

        # Ex-Dividend
        ex_div = info.get("exDividendDate")
        if ex_div:
            if isinstance(ex_div, (int, float)):
                try:
                    dt = datetime.fromtimestamp(ex_div, tz=timezone.utc)
                    sections.append(f"- **Ex-Dividend Date:** {dt.strftime('%B %d, %Y')}")
                except Exception:
                    sections.append(f"- **Ex-Dividend Date:** {ex_div}")
            else:
                sections.append(f"- **Ex-Dividend Date:** {str(ex_div)[:10]}")
        else:
            sections.append("- **Ex-Dividend Date:** N/A (no dividend)")

        # --- Web Search for Catalysts ---
        if DDGS:
            sections.append("\n### Recent Catalyst News (Web Search)")
            try:
                ddgs = DDGS()
                results = ddgs.text(
                    f"{company} {ticker} upcoming earnings catalyst product launch 2024 2025",
                    max_results=8
                )
                if results:
                    for r in results:
                        title = r.get("title", "")
                        body = r.get("body", "")[:200]
                        href = r.get("href", "")
                        sections.append(f"\n**{title}**")
                        sections.append(f"{body}...")
                        sections.append(f"[Source]({href})")
            except Exception as e:
                sections.append(f"Web search error: {e}")
        else:
            sections.append("\n*Web search unavailable (ddgs not installed)*")

        return "\n".join(sections)

    except Exception as e:
        return f"Error fetching upcoming catalysts for {ticker}: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# Tool 4 — Insider Activity
# ─────────────────────────────────────────────────────────────────────────────

@tool
def get_insider_activity(ticker: str) -> str:
    """
    Fetch recent insider transactions (buys and sells) for a stock including
    insider name, role, shares, transaction value, and type.
    """
    try:
        stock = yf.Ticker(ticker)
        sections = [f"## Insider Activity — {ticker}\n"]

        # --- Insider Transactions ---
        try:
            tx = stock.insider_transactions
            if tx is not None and not tx.empty:
                sections.append("### Recent Insider Transactions (Last 15)")
                sections.append("| Date | Insider | Shares | Value | Transaction |")
                sections.append("|------|---------|--------|-------|-------------|")
                for _, row in tx.head(15).iterrows():
                    date_str = str(row.get("startDate", ""))[:10] if "startDate" in row else str(row.get("Date", ""))[:10]
                    insider = row.get("Insider", row.get("filerName", "N/A"))
                    shares = row.get("Shares", row.get("shares", 0))
                    value = row.get("Value", row.get("value", 0))
                    tx_type = row.get("Transaction", row.get("transactionType", "N/A"))
                    shares_str = f"{int(shares):,}" if shares else "N/A"
                    value_str = f"${int(value):,}" if value else "N/A"
                    tag = "[BUY]" if "Buy" in str(tx_type) or "Purchase" in str(tx_type) else "[SELL]"
                    sections.append(f"| {date_str} | {insider} | {shares_str} | {value_str} | {tag} {tx_type} |")
            else:
                sections.append("No insider transaction data available.")
        except Exception as e:
            sections.append(f"Could not fetch insider transactions: {e}")

        # --- Insider Purchases Summary ---
        try:
            ip = stock.insider_purchases
            if ip is not None and not ip.empty:
                sections.append("\n### Insider Purchase Summary")
                sections.append(ip.to_markdown())
        except Exception:
            pass

        return "\n".join(sections)

    except Exception as e:
        return f"Error fetching insider activity for {ticker}: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# Tool 5 — Institutional Holdings
# ─────────────────────────────────────────────────────────────────────────────

@tool
def get_institutional_changes(ticker: str) -> str:
    """
    Get top institutional holders, their position sizes, and quarter-over-quarter
    changes in institutional ownership for a stock.
    """
    try:
        stock = yf.Ticker(ticker)
        sections = [f"## Institutional & Mutual Fund Holdings — {ticker}\n"]

        # --- Top Institutional Holders ---
        try:
            ih = stock.institutional_holders
            if ih is not None and not ih.empty:
                sections.append("### Top Institutional Holders")
                sections.append("| Holder | Shares | % Out | Value | Date Reported |")
                sections.append("|--------|--------|-------|-------|---------------|")
                for _, row in ih.head(10).iterrows():
                    holder = row.get("Holder", "N/A")
                    shares = row.get("Shares", 0)
                    pct = row.get("% Out", row.get("pctHeld", 0))
                    val = row.get("Value", 0)
                    date_rep = str(row.get("Date Reported", ""))[:10]
                    pct_str = f"{float(pct)*100:.2f}%" if pct else "N/A"
                    val_str = f"${int(val):,}" if val else "N/A"
                    shares_str = f"{int(shares):,}" if shares else "N/A"
                    sections.append(f"| {holder} | {shares_str} | {pct_str} | {val_str} | {date_rep} |")
            else:
                sections.append("No institutional holder data available.")
        except Exception as e:
            sections.append(f"Could not fetch institutional holders: {e}")

        # --- Mutual Fund Holders ---
        try:
            mf = stock.mutualfund_holders
            if mf is not None and not mf.empty:
                sections.append("\n### Top Mutual Fund Holders")
                sections.append("| Fund | Shares | % Out | Value |")
                sections.append("|------|--------|-------|-------|")
                for _, row in mf.head(8).iterrows():
                    holder = row.get("Holder", "N/A")
                    shares = row.get("Shares", 0)
                    pct = row.get("% Out", row.get("pctHeld", 0))
                    val = row.get("Value", 0)
                    pct_str = f"{float(pct)*100:.2f}%" if pct else "N/A"
                    val_str = f"${int(val):,}" if val else "N/A"
                    shares_str = f"{int(shares):,}" if shares else "N/A"
                    sections.append(f"| {holder} | {shares_str} | {pct_str} | {val_str} |")
        except Exception:
            pass

        # Summary stats
        try:
            info = stock.info
            inst_pct = info.get("heldPercentInstitutions")
            insider_pct = info.get("heldPercentInsiders")
            float_shares = info.get("floatShares")
            sections.append("\n### Ownership Summary")
            sections.append(f"- **Institutional Ownership:** {_pct(inst_pct)}" if inst_pct else "- **Institutional Ownership:** N/A")
            sections.append(f"- **Insider Ownership:** {_pct(insider_pct)}" if insider_pct else "- **Insider Ownership:** N/A")
            if float_shares:
                sections.append(f"- **Float Shares:** {float_shares/1e6:.1f}M")
        except Exception:
            pass

        return "\n".join(sections)

    except Exception as e:
        return f"Error fetching institutional changes for {ticker}: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# Tool 6 — Company Operations & Intelligence
# ─────────────────────────────────────────────────────────────────────────────

@tool
def search_company_operations(ticker: str) -> str:
    """
    Gather live intelligence about company operations: number of employees,
    key office/factory locations, business segments, recent expansions,
    partnerships, and strategic moves via web search.
    """
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        company = info.get("longName", ticker)
        country = info.get("country", "")
        city = info.get("city", "")
        industry = info.get("industry", "")
        sector = info.get("sector", "")
        employees = info.get("fullTimeEmployees")
        website = info.get("website", "")
        description = info.get("longBusinessSummary", "")

        sections = [f"## Company Operations Intelligence — {company} ({ticker})\n"]

        sections.append("### Company Profile")
        sections.append(f"- **Headquarters:** {city}, {country}")
        sections.append(f"- **Sector / Industry:** {sector} / {industry}")
        sections.append(f"- **Full-Time Employees:** {f'{employees:,}' if employees else 'N/A'}")
        sections.append(f"- **Website:** {website}")

        if description:
            sections.append(f"\n**Business Overview:**\n{description[:800]}...")

        # --- Web search for operational details ---
        if DDGS:
            # Search 1: Locations/offices/factories
            sections.append("\n### Global Locations & Operations (Web Search)")
            try:
                ddgs = DDGS()
                results = ddgs.text(
                    f"{company} offices factories locations countries operations global footprint",
                    max_results=5
                )
                if results:
                    for r in results:
                        title = r.get("title", "")
                        body = r.get("body", "")[:250]
                        sections.append(f"\n**{title}**\n{body}")
            except Exception as e:
                sections.append(f"Location search error: {e}")

            # Search 2: Recent strategic moves
            sections.append("\n### Recent Strategic Moves & Expansions")
            try:
                ddgs2 = DDGS()
                results2 = ddgs2.text(
                    f"{company} expansion partnership acquisition deal 2024 2025 strategy",
                    max_results=5
                )
                if results2:
                    for r in results2:
                        title = r.get("title", "")
                        body = r.get("body", "")[:250]
                        sections.append(f"\n**{title}**\n{body}")
            except Exception as e:
                sections.append(f"Strategic search error: {e}")

            # Search 3: India-specific or US-specific market data
            sections.append("\n### Market Position & Competitive Intelligence")
            try:
                ddgs3 = DDGS()
                results3 = ddgs3.text(
                    f"{company} market share competitors 2024 2025 industry position",
                    max_results=4
                )
                if results3:
                    for r in results3:
                        title = r.get("title", "")
                        body = r.get("body", "")[:200]
                        sections.append(f"\n**{title}**\n{body}")
            except Exception as e:
                sections.append(f"Market position search error: {e}")
        else:
            sections.append("\n*Web search unavailable (ddgs not installed)*")

        return "\n".join(sections)

    except Exception as e:
        return f"Error fetching company operations for {ticker}: {e}"
