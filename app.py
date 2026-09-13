"""
Streamlit UI for InvestAI.
"""
import streamlit as st
import plotly.graph_objects as go
import yfinance as yf
import pandas as pd
import json
from pathlib import Path
from datetime import datetime
from invest_ai.agents.graph import research_graph
from invest_ai.utils.ticker import resolve_ticker, get_currency_symbol
from invest_ai.utils.pdf import generate_pdf_report
from invest_ai.utils.holdings import parse_holdings_excel, aggregate_portfolio_data
from invest_ai.agents.portfolio import run_portfolio_review_agent
from invest_ai.utils.dashboards import (
    get_us_etf_holdings,
    get_nifty_50_constituents,
    get_nifty_next_50_constituents,
    get_bank_nifty_constituents,
    get_fii_dii_holdings,
    get_trending_stocks
)
from invest_ai.utils.swing import get_swing_snapshot

WATCHLIST_FILE = Path(__file__).parent / ".invest_ai_watchlist.json"
YFINANCE_CACHE_DIR = Path(__file__).parent / ".yfinance_cache"
# Some managed Windows installations restrict yfinance's profile cache. Keep its
# SQLite cache alongside the app so live quotes work consistently.
yf.set_tz_cache_location(str(YFINANCE_CACHE_DIR))


def load_watchlist() -> list[str]:
    """Load a small local watchlist; malformed files are safely ignored."""
    try:
        items = json.loads(WATCHLIST_FILE.read_text(encoding="utf-8"))
        return items if isinstance(items, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def save_watchlist(items: list[str]) -> None:
    WATCHLIST_FILE.write_text(json.dumps(sorted(set(items)), indent=2), encoding="utf-8")

# --- Page Config ---
st.set_page_config(
    page_title="InvestAI - Agentic Research",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Custom CSS ---
st.markdown("""
<style>
    .stApp {
        background-color: #0E1117;
        color: #FAFAFA;
    }
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        background: -webkit-linear-gradient(45deg, #FF4B2B, #FF416C);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0px;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #A0AEC0;
        margin-bottom: 2rem;
    }
    div[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #101827 0%, #151b2d 100%);
        border-right: 1px solid #2D3748;
    }
    .swing-hero {
        background: radial-gradient(circle at top right, rgba(56, 189, 248, .18), transparent 32%),
                    linear-gradient(120deg, #111c31, #111827 52%, #172554);
        border: 1px solid rgba(96, 165, 250, .32);
        border-radius: 18px;
        padding: 1.35rem 1.5rem;
        margin: 0.5rem 0 1.25rem;
        box-shadow: 0 16px 38px rgba(0, 0, 0, .18);
    }
    .swing-kicker { color: #7dd3fc; font-size: .78rem; font-weight: 800; letter-spacing: .11em; text-transform: uppercase; }
    .swing-title { color: #f8fafc; font-size: 1.7rem; font-weight: 750; margin: .25rem 0; }
    .swing-copy { color: #b8c6db; margin: 0; max-width: 760px; }
    .stButton > button[kind="primary"] {
        background: linear-gradient(90deg, #0284c7, #2563eb);
        border: 0;
        border-radius: 9px;
        font-weight: 700;
    }
    div[data-testid="stMetric"] {
        background: #131d30;
        border: 1px solid #273853;
        border-radius: 12px;
        padding: .6rem .8rem;
    }
    div[data-testid="stDataFrame"] { border: 1px solid #263754; border-radius: 12px; overflow: hidden; }
</style>
""", unsafe_allow_html=True)

# --- Functions ---
def plot_candlestick(ticker: str, period="6mo"):
    try:
        df = yf.Ticker(ticker).history(period=period)
        if df.empty:
            return None
        
        cur = get_currency_symbol(ticker)
        fig = go.Figure(data=[go.Candlestick(x=df.index,
                        open=df['Open'],
                        high=df['High'],
                        low=df['Low'],
                        close=df['Close'],
                        name="Price")])
        
        fig.update_layout(
            title=f"{ticker} - {period} Price Action",
            yaxis_title=f"Price ({cur})",
            xaxis_title="Date",
            template="plotly_dark",
            margin=dict(l=20, r=20, t=40, b=20),
            height=400,
            xaxis_rangeslider_visible=False
        )
        return fig
    except Exception as e:
        st.error(f"Failed to load chart: {e}")
        return None

def stream_report(text):
    for word in text.split(" "):
        yield word + " "
        import time
        time.sleep(0.02)

# --- Sidebar ---
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    
    app_mode = st.radio("Mode", ["Single Stock Research", "Swing Watchlist", "Compare Stocks", "Thematic Screener", "Dashboards", "Dividend Target Planner", "Live Intelligence Report", "Live News Report", "Family Portfolio Review"])
    
    market = st.radio("Target Market", ["India (NSE/BSE)", "US (NYSE/NASDAQ)"])
    market_val = "india" if "India" in market else "us"
    
    st.markdown("### 🔍 Research Target")
    
    if app_mode == "Single Stock Research":
        raw_ticker = st.text_input("Enter Ticker Symbol", placeholder="e.g. RELIANCE or AAPL").upper()
        depth = st.selectbox("Analysis Depth", [
            "Full Deep Dive (Tech, Fund, News)",
            "Technical Analysis Only",
            "Fundamental Analysis Only",
            "Dividend Yield Report",
            "Economic Moat Report"
        ])
    elif app_mode == "Swing Watchlist":
        st.markdown("Build a persistent list, then run a one-year daily technical screen on demand.")
        watchlist = load_watchlist()
        if not watchlist and market_val == "india":
            if st.button("Load sample small/mid-cap basket", use_container_width=True, help="Examples only for testing the scanner; this is not a recommendation list."):
                save_watchlist(["KAYNES.NS", "SULA.NS", "CAMPUS.NS"])
                st.rerun()
        new_symbol = st.text_input("Add stock to watchlist", placeholder="e.g. RELIANCE or AAPL", key="watchlist_symbol").upper().strip()
        add_stock = st.button("Add to watchlist", use_container_width=True)
        if add_stock and new_symbol:
            resolved = resolve_ticker(new_symbol, market_val)
            if resolved not in watchlist:
                save_watchlist(watchlist + [resolved])
                st.success(f"Added {resolved}")
            else:
                st.info(f"{resolved} is already in the watchlist.")
            watchlist = load_watchlist()
        if watchlist:
            remove_symbols = st.multiselect("Remove stocks", watchlist, key="watchlist_remove")
            if st.button("Remove selected", disabled=not remove_symbols, use_container_width=True):
                save_watchlist([item for item in watchlist if item not in remove_symbols])
                st.rerun()
            st.caption(f"{len(watchlist)} stock(s): {', '.join(watchlist)}")
        else:
            st.info("Add one or more stocks to start your screen.")
        raw_ticker = "SwingWatchlist"
        depth = "N/A"
    elif app_mode == "Compare Stocks":
        raw_ticker = st.text_input("Enter Tickers (comma-separated)", placeholder="e.g. AAPL, MSFT, GOOGL").upper()
        depth = "Comparison Report"
    elif app_mode == "Dashboards":
        st.markdown("Explore comprehensive dashboards for ETFs and stock trends.")
        raw_ticker = "Dashboards"  # Dummy value to pass the 'if not raw_ticker' check
        depth = "N/A"
    elif app_mode == "Dividend Target Planner":
        st.markdown("Plan your dividend investment portfolio to reach your targets.")
        div_target = st.number_input("Target Dividend Income", min_value=1.0, value=12000.0 if market_val == "us" else 120000.0, step=500.0)
        target_freq = st.selectbox("Target Frequency", ["Annual", "Monthly"])
        num_stocks = st.slider("Number of High-Dividend Stocks", min_value=3, max_value=15, value=5)
        pref_prompt = st.text_area("Custom Constraints / Preferences", placeholder="e.g. Focus on safety and sector diversity")
        raw_ticker = "DividendPlanner"
        depth = "N/A"
    elif app_mode == "Live Intelligence Report":
        raw_ticker = st.text_input("Enter Ticker Symbol", placeholder="e.g. AAPL or RELIANCE").upper()
        depth = "Live Intelligence Report"
        st.markdown("""<div style='background: linear-gradient(135deg, #1a1a2e, #16213e);
            border: 1px solid #e94560; border-radius: 8px; padding: 10px; margin-top: 8px;'>
            <span style='color:#e94560; font-weight:700;'>🔴 LIVE</span>
            <span style='color:#a0aec0; font-size:0.85rem;'> Fetches real-time earnings, analyst estimates,
            insider activity, catalysts & company intelligence from the internet.</span>
            </div>""", unsafe_allow_html=True)
    elif app_mode == "Live News Report":
        raw_ticker = st.text_input("Enter Ticker Symbol", placeholder="e.g. AAPL or RELIANCE").upper()
        depth = "Live News Report"
        st.markdown("""<div style='background: linear-gradient(135deg, #1a1a2e, #16213e);
            border: 1px solid #ff6b35; border-radius: 8px; padding: 10px; margin-top: 8px;'>
            <span style='color:#ff6b35; font-weight:700;'>📰 LIVE</span>
            <span style='color:#a0aec0; font-size:0.85rem;'> Fetches real-time news, sentiment, breaking developments,
            and live event intelligence from news sources.</span>
            </div>""", unsafe_allow_html=True)
    elif app_mode == "Family Portfolio Review":
        st.markdown("""<div style='background: linear-gradient(135deg, #1e1b4b, #311042);
            border: 1px solid #c084fc; border-radius: 8px; padding: 10px; margin-top: 8px;'>
            <span style='color:#c084fc; font-weight:700;'>💼 PORTFOLIO</span>
            <span style='color:#cbd5e1; font-size:0.85rem;'> Analyze family asset classes, holdings allocations, categories, and generate strategic reviews.</span>
            </div>""", unsafe_allow_html=True)
        raw_ticker = "PortfolioReview"
        depth = "N/A"
    else:
        raw_ticker = st.text_input("Enter Investment Theme", placeholder="e.g. AI Semiconductors or Renewable Energy")
        depth = "Thematic Screener Report"
    
    st.markdown("---")
    st.markdown("💡 *Tip: For Indian stocks, we auto-append `.NS` if needed.*")

# --- Main App ---
st.markdown('<p class="main-header">InvestAI</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Agentic Stock Research Platform</p>', unsafe_allow_html=True)

if not raw_ticker:
    st.info("👈 Enter your target in the sidebar to begin.")
else:
    # Resolve ticker(s) or use theme directly
    if app_mode == "Single Stock Research":
        ticker = resolve_ticker(raw_ticker, market_val)
        st.subheader(f"Analyzing: `{ticker}`")
        # Display Chart
        chart_fig = plot_candlestick(ticker)
        if chart_fig:
            st.plotly_chart(chart_fig, use_container_width=True)
    elif app_mode == "Swing Watchlist":
        ticker = "SwingWatchlist"
        watchlist = load_watchlist()
        st.markdown("""
        <section class="swing-hero">
          <div class="swing-kicker">Daily swing scanner</div>
          <div class="swing-title">📋 Swing Trading Watchlist</div>
          <p class="swing-copy">Screen price action first, then ask the research agent to challenge the setup with company, catalyst and small-cap risk context. Signals are educational—not a promise of next-day performance.</p>
        </section>
        """, unsafe_allow_html=True)
        if not watchlist:
            st.info("Add stocks in the sidebar, then run the screen.")
        else:
            scan_col, detail_col = st.columns([1, 1])
            with scan_col:
                run_swing_scan = st.button("🔎 Run watchlist analysis", type="primary", use_container_width=True)
            with detail_col:
                selected_swing_ticker = st.selectbox("Chart detail", watchlist)

            if run_swing_scan:
                rows, failures = [], []
                progress = st.progress(0, text="Starting daily technical screen...")
                for index, symbol in enumerate(watchlist, start=1):
                    _, snapshot, error = get_swing_snapshot(symbol)
                    if snapshot:
                        rows.append(snapshot)
                    else:
                        failures.append(f"{symbol}: {error}")
                    progress.progress(index / len(watchlist), text=f"Analyzing {symbol} ({index}/{len(watchlist)})")
                progress.empty()
                st.session_state["swing_screen"] = rows
                st.session_state["swing_failures"] = failures

            screen_rows = st.session_state.get("swing_screen", [])
            if screen_rows:
                screen_df = pd.DataFrame(screen_rows).sort_values("Score", ascending=False)
                display_columns = ["Ticker", "Signal", "Score", "Price", "RSI (14)", "ADX (14)", "+DI", "-DI", "Volume / 20d", "ATR %", "As of", "Setup"]
                st.markdown("### Latest screen")
                st.dataframe(
                    screen_df[display_columns].style.format({
                        "Price": "{:.2f}", "RSI (14)": "{:.1f}", "ADX (14)": "{:.1f}",
                        "+DI": "{:.1f}", "-DI": "{:.1f}", "Volume / 20d": "{:.2f}x", "ATR %": "{:.2f}%",
                    }),
                    use_container_width=True,
                    hide_index=True,
                )
                st.download_button(
                    "Download latest screen (CSV)",
                    screen_df.to_csv(index=False).encode("utf-8"),
                    file_name=f"swing_watchlist_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                )
                for issue in st.session_state.get("swing_failures", []):
                    st.warning(issue)

            chart_data, detail_snapshot, detail_error = get_swing_snapshot(selected_swing_ticker)
            if detail_error:
                st.warning(detail_error)
            elif chart_data is not None and detail_snapshot is not None:
                st.markdown(f"### One-year chart: `{selected_swing_ticker}` — {detail_snapshot['Signal']}")
                fig = go.Figure()
                fig.add_trace(go.Candlestick(
                    x=chart_data.index, open=chart_data["Open"], high=chart_data["High"],
                    low=chart_data["Low"], close=chart_data["Close"], name="Price",
                ))
                for column, label, color in [("SMA20", "SMA 20", "#60A5FA"), ("SMA50", "SMA 50", "#FBBF24"), ("SMA200", "SMA 200", "#F472B6")]:
                    fig.add_trace(go.Scatter(x=chart_data.index, y=chart_data[column], name=label, line=dict(color=color, width=1.3)))
                fig.update_layout(template="plotly_dark", height=480, margin=dict(l=20, r=20, t=35, b=20), xaxis_rangeslider_visible=False, yaxis_title="Price")
                st.plotly_chart(fig, use_container_width=True)
                metrics = st.columns(5)
                metrics[0].metric("Signal", detail_snapshot["Signal"], f"Score {detail_snapshot['Score']:+d}")
                metrics[1].metric("RSI (14)", f"{detail_snapshot['RSI (14)']:.1f}")
                metrics[2].metric("ADX (14)", f"{detail_snapshot['ADX (14)']:.1f}", f"+DI {detail_snapshot['+DI']:.1f} / -DI {detail_snapshot['-DI']:.1f}")
                metrics[3].metric("Volume", f"{detail_snapshot['Volume / 20d']:.2f}x", "vs 20-day avg")
                metrics[4].metric("ATR risk", f"{detail_snapshot['ATR %']:.2f}%", "14-day average range")
                with st.expander("How the signal is scored"):
                    st.write(detail_snapshot["Setup"] or "No decisive setup.")
                    st.caption("BUY requires several aligned trend and momentum conditions. A signal is a screening aid only; confirm price action, liquidity, news/events, position size, and your own risk limits before trading.")

                st.markdown("### 🤖 Agent setup review")
                st.caption("Run this only for a shortlisted name. The agent reviews the technical setup alongside fundamentals and recent news; it can disagree with the screen.")
                agent_focus = st.selectbox(
                    "Review focus",
                    ["Swing trade validation", "Small-cap risk check", "Catalyst and news check"],
                    key="swing_agent_focus",
                )
                if st.button("Run agent review for selected stock", type="primary", use_container_width=True):
                    agent_query = f"""Review {selected_swing_ticker} as a potential 2-15 trading-day swing trade.
Technical screen snapshot: signal={detail_snapshot['Signal']}, score={detail_snapshot['Score']}, RSI={detail_snapshot['RSI (14)']:.1f}, ADX={detail_snapshot['ADX (14)']:.1f}, +DI={detail_snapshot['+DI']:.1f}, -DI={detail_snapshot['-DI']:.1f}, volume ratio={detail_snapshot['Volume / 20d']:.2f}x, ATR={detail_snapshot['ATR %']:.2f}%.
Focus: {agent_focus}. Use technical, fundamental and news analysis. Give a concise verdict: VALIDATE, WAIT, or REJECT. Explain catalysts, invalidation risks, liquidity/volatility concerns, and what must happen at the next daily close. Do not present this as financial advice."""
                    agent_state = {
                        "messages": [], "mode": "single", "ticker": selected_swing_ticker,
                        "market": market_val, "query": agent_query, "agents_to_call": [],
                        "agents_called": [], "technical_analysis": None, "fundamental_analysis": None,
                        "news_analysis": None, "dividend_analysis": None, "moat_analysis": None,
                        "comparison_analysis": None, "screener_analysis": None,
                        "live_intel_analysis": None, "live_news_analysis": None,
                        "final_report": None, "company_name": None, "current_price": None, "error": None,
                    }
                    with st.status("🤖 Research agent reviewing the setup...", expanded=True) as status:
                        st.write("Reading the technical setup, company context, and recent news...")
                        try:
                            agent_result = research_graph.invoke(agent_state)
                            st.session_state["swing_agent_report"] = {
                                "ticker": selected_swing_ticker,
                                "report": agent_result.get("final_report", "No report generated."),
                                "agents": agent_result.get("agents_called", []),
                            }
                            status.update(label="✅ Agent review complete", state="complete", expanded=False)
                        except Exception as exc:
                            status.update(label="❌ Agent review failed", state="error", expanded=True)
                            st.error(f"Agent review failed: {exc}")
                agent_report = st.session_state.get("swing_agent_report")
                if agent_report and agent_report["ticker"] == selected_swing_ticker:
                    st.markdown(f"#### Agent review: `{selected_swing_ticker}`")
                    st.caption(f"Specialists consulted: {', '.join(agent_report['agents']).title() or 'Unavailable'}")
                    st.markdown(agent_report["report"])
    elif app_mode == "Compare Stocks":
        tickers = [resolve_ticker(t.strip(), market_val) for t in raw_ticker.split(",") if t.strip()]
        ticker = ", ".join(tickers)
        st.subheader(f"Comparing: `{ticker}`")
    elif app_mode == "Thematic Screener":
        ticker = raw_ticker
        st.subheader(f"Screening Theme: `{ticker}`")
    elif app_mode == "Dashboards":
        st.subheader("Market Dashboards")
        ticker = "Dashboards"
        
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "🇮🇳 Indian ETFs", 
            "🇮🇳 Indian Mutual Funds",
            "🌎 US / Global ETFs", 
            "🏦 FII / DII Holdings (India)", 
            "📈 Trending Stocks"
        ])
        
        with tab1:
            st.markdown("### Indian Index ETFs & Mutual Funds")
            st.write("View the underlying constituents of popular Indian index ETFs.")
            ind_etf = st.selectbox("Select Indian ETF", ["NIFTYBEES.NS (Nifty 50)", "JUNIORBEES.NS (Nifty Next 50)", "BANKBEES.NS (Bank Nifty)"])
            with st.spinner("Fetching data..."):
                if "NIFTYBEES" in ind_etf:
                    df_ind = get_nifty_50_constituents()
                elif "JUNIORBEES" in ind_etf:
                    df_ind = get_nifty_next_50_constituents()
                else:
                    df_ind = get_bank_nifty_constituents()
                
                if not df_ind.empty:
                    st.dataframe(df_ind, use_container_width=True)
                else:
                    st.warning("Could not fetch index constituents at this time.")
                    
        with tab2:
            st.markdown("### Indian Mutual Funds")
            st.write("View the underlying top holdings of major Indian Mutual Funds with live market data.")
            indian_mfs = {
                "Parag Parikh Flexi Cap Fund": "0P0000XW8F.BO",
                "SBI Small Cap Fund": "0P0000XVUR.BO",
                "Mirae Asset Large Cap Fund": "0P0000XVAA.BO",
                "Nippon India Small Cap Fund": "0P0000XWA1.BO",
                "Axis Bluechip Fund": "0P00005WLZ.BO"
            }
            selected_mf = st.selectbox("Select Indian Mutual Fund", list(indian_mfs.keys()))
            with st.spinner("Fetching live top holdings and market data..."):
                df_mf = get_us_etf_holdings(indian_mfs[selected_mf])
                if not df_mf.empty:
                    # Format Holding Percent
                    if 'Holding Percent' in df_mf.columns:
                        df_mf['Holding Percent'] = df_mf['Holding Percent'].apply(lambda x: f"{x*100:.2f}%" if pd.notnull(x) else "N/A")
                    st.dataframe(df_mf, use_container_width=True)
                else:
                    st.warning("No holdings data available for this mutual fund.")
                    
        with tab3:
            st.markdown("### US & Global ETFs")
            us_etfs = {
                "SPY (S&P 500)": "SPY",
                "QQQ (Nasdaq 100)": "QQQ",
                "VTI (Total Market)": "VTI",
                "IWM (Russell 2000)": "IWM",
                "SCHD (Dividend Equity)": "SCHD",
                "BOTZ (Robotics & AI)": "BOTZ",
                "AIQ (AI & Tech)": "AIQ",
                "SMH (Semiconductors)": "SMH",
                "SOXX (Semiconductors)": "SOXX",
                "QTUM (Quantum Computing)": "QTUM",
                "ARKK (Innovation)": "ARKK",
                "ARKG (Genomics)": "ARKG",
                "URTH (MSCI World)": "URTH",
                "GLD (Gold)": "GLD",
                "JEPI (JPMorgan Equity Premium)": "JEPI",
                "XLF (Financials)": "XLF",
                "XLV (Health Care)": "XLV",
                "XLE (Energy)": "XLE",
                "VNQ (Real Estate)": "VNQ",
                "XLU (Utilities)": "XLU"
            }
            selected_us_etf = st.selectbox("Select US/Global ETF", list(us_etfs.keys()))
            with st.spinner("Fetching live top holdings and market data..."):
                df_us = get_us_etf_holdings(us_etfs[selected_us_etf])
                if not df_us.empty:
                    if 'Holding Percent' in df_us.columns:
                        df_us['Holding Percent'] = df_us['Holding Percent'].apply(lambda x: f"{x*100:.2f}%" if pd.notnull(x) else "N/A")
                    st.dataframe(df_us, use_container_width=True)
                else:
                    st.warning("No holdings data available for this ETF via standard API.")
                    
        with tab4:
            st.markdown("### Institutional Holdings (India)")
            st.write("Top Indian stocks sorted by their Institutional Holding %.")
            
            holding_type = st.radio("Holding Type", ["Overall Institutional (Avg)", "FII Only", "DII Only"], horizontal=True)
            if holding_type != "Overall Institutional (Avg)":
                st.info("💡 Note: Free live APIs do not consistently separate FII and DII. Displaying Overall Institutional (FII + DII) fallback data.")

            with st.spinner("Fetching institutional holdings data from Yahoo Finance..."):
                # Use all Nifty 50 components dynamically
                nifty_df = get_nifty_50_constituents()
                if not nifty_df.empty and 'Symbol' in nifty_df.columns:
                    sample_nifty_stocks = [sym + ".NS" for sym in nifty_df['Symbol'].tolist()[:30]] # Taking top 30 to keep API fast
                else:
                    sample_nifty_stocks = [
                        "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS", 
                        "HINDUNILVR.NS", "SBIN.NS", "BHARTIARTL.NS", "ITC.NS", "KOTAKBANK.NS"
                    ]
                
                df_inst = get_fii_dii_holdings(sample_nifty_stocks)
                if not df_inst.empty:
                    st.dataframe(df_inst, use_container_width=True)
                else:
                    st.warning("Could not fetch institutional data.")
                    
        with tab5:
            st.markdown("### Trending Stocks (US & India)")
            st.write("Sorted by percentage change over the last 2 days.")
            trending_pool = [
                "NVDA", "AAPL", "MSFT", "TSLA", "META", "AMZN", "GOOGL", "AMD", "PLTR", "AVGO", "CRWD", "NFLX"
            ]
            
            # Combine US pool with Nifty 50 stocks
            nifty_df_trend = get_nifty_50_constituents()
            if not nifty_df_trend.empty and 'Symbol' in nifty_df_trend.columns:
                indian_pool = [sym + ".NS" for sym in nifty_df_trend['Symbol'].tolist()[:30]] # Taking top 30
                trending_pool.extend(indian_pool)
            else:
                trending_pool.extend(["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ZOMATO.NS", "TATAMOTORS.NS"])
                
            with st.spinner("Calculating recent movements..."):
                df_trend = get_trending_stocks(trending_pool)
                if not df_trend.empty:
                    st.dataframe(df_trend, use_container_width=True)
                else:
                    st.warning("Could not fetch trending data.")

    elif app_mode == "Dividend Target Planner":
        st.subheader("🎯 Dividend Target Planner")
        st.write("Let the Agent select high-dividend stocks and allocate your investment to reach your target dividend income, then project compound growth over 5 and 10 years.")
        
        # User parameters inside main pane
        col_g1, col_g2, col_g3 = st.columns(3)
        with col_g1:
            exp_cap_appr = st.number_input(
                "Expected Capital Appreciation (%/yr)",
                min_value=0.0, max_value=30.0,
                value=7.0 if market_val == "us" else 10.0,
                step=0.5
            )
        with col_g2:
            exp_div_growth = st.number_input(
                "Expected Dividend Growth (%/yr)",
                min_value=0.0, max_value=25.0,
                value=5.0 if market_val == "us" else 6.0,
                step=0.5
            )
        with col_g3:
            alloc_strategy = st.selectbox("Allocation Strategy", ["Equal Weight", "Yield-Weighted"])

        run_planner = st.button("🚀 Run Agentic Dividend Planner", type="primary", use_container_width=True)
        
        if run_planner:
            # Step 1: Fetch candidate data
            with st.spinner("Fetching live candidate dividend stocks..."):
                from invest_ai.utils.dashboards import get_dividend_candidate_data
                candidates_df = get_dividend_candidate_data(market_val)
                
            if candidates_df.empty:
                st.error("Could not fetch candidate stocks from Yahoo Finance.")
            else:
                # Step 2: Call Agent to select stocks
                with st.status("🤖 Agent analyzing dividend profiles and selecting stocks...", expanded=True) as status:
                    from invest_ai.agents.dividend import run_dividend_planner_agent
                    st.write("🔄 Evaluating candidate yields and payout ratios...")
                    st.write(f"📊 Screening for {num_stocks} stocks with sector diversification...")
                    selected_tickers, explanation = run_dividend_planner_agent(
                        candidates_df=candidates_df,
                        num_stocks=num_stocks,
                        target_income=div_target,
                        frequency=target_freq,
                        market=market_val,
                        preferences=pref_prompt
                    )
                    status.update(label="✅ Agent Portfolio Design Complete!", state="complete", expanded=False)
                
                # Check that we got stocks
                selected_df = candidates_df[candidates_df["Symbol"].isin(selected_tickers)].copy()
                if selected_df.empty:
                    # Fallback to top N
                    selected_df = candidates_df.head(num_stocks).copy()
                    selected_tickers = selected_df["Symbol"].tolist()
                    st.warning("Agent selection was empty or invalid. Fell back to highest yield candidate stocks.")
                
                st.markdown("### 📋 Agent Selection & Investment Allocation")
                
                # Calculate weights and allocations
                N = len(selected_df)
                if alloc_strategy == "Equal Weight":
                    selected_df["Weight (%)"] = 100.0 / N
                else:  # Yield-Weighted
                    total_yield = selected_df["Yield (%)"].sum()
                    if total_yield > 0:
                        selected_df["Weight (%)"] = (selected_df["Yield (%)"] / total_yield) * 100.0
                    else:
                        selected_df["Weight (%)"] = 100.0 / N
                
                # Portfolio Average Yield (weighted sum)
                portfolio_avg_yield = (selected_df["Yield (%)"] * selected_df["Weight (%)"] / 100.0).sum()
                
                # Required Investment
                target_annual = div_target if target_freq == "Annual" else div_target * 12
                required_total_inv = target_annual / (portfolio_avg_yield / 100.0) if portfolio_avg_yield > 0 else 0.0
                
                # Allocations per stock
                selected_df["Investment Amount"] = selected_df["Weight (%)"] / 100.0 * required_total_inv
                selected_df["Shares to Buy"] = selected_df.apply(
                    lambda r: int(r["Investment Amount"] / r["Price"]) if r["Price"] > 0 else 0,
                    axis=1
                )
                selected_df["Expected Year 1 Dividend"] = selected_df["Shares to Buy"] * selected_df["Dividend Rate"]
                
                # Formatting currency
                cur = "₹" if market_val == "india" else "$"
                
                # Summary Metric Cards
                c_m1, c_m2, c_m3 = st.columns(3)
                c_m1.metric("Required Total Investment", f"{cur}{required_total_inv:,.2f}")
                c_m2.metric("Portfolio Weighted Yield", f"{portfolio_avg_yield:.2f}%")
                c_m3.metric("Expected Year 1 Dividend", f"{cur}{selected_df['Expected Year 1 Dividend'].sum():,.2f}")
                
                # Display table
                disp_df = selected_df[[
                    "Symbol", "Name", "Price", "Yield (%)", "Payout Ratio (%)",
                    "Weight (%)", "Investment Amount", "Shares to Buy", "Expected Year 1 Dividend"
                ]].copy()
                
                # Format columns
                disp_df["Price"] = disp_df["Price"].apply(lambda x: f"{cur}{x:,.2f}")
                disp_df["Yield (%)"] = disp_df["Yield (%)"].apply(lambda x: f"{x:.2f}%")
                disp_df["Payout Ratio (%)"] = disp_df["Payout Ratio (%)"].apply(lambda x: f"{x:.2f}%")
                disp_df["Weight (%)"] = disp_df["Weight (%)"].apply(lambda x: f"{x:.2f}%")
                disp_df["Investment Amount"] = disp_df["Investment Amount"].apply(lambda x: f"{cur}{x:,.2f}")
                disp_df["Expected Year 1 Dividend"] = disp_df["Expected Year 1 Dividend"].apply(lambda x: f"{cur}{x:,.2f}")
                
                st.dataframe(disp_df, use_container_width=True, hide_index=True)
                
                # Agent Explanation
                with st.expander("🔬 View Agent Analyst Reasoning"):
                    st.markdown(explanation)
                
                # --- Growth Projections (5 and 10 years) ---
                st.markdown("### 📈 Dividend & Portfolio Growth Projections")
                st.write("Below are the 5 and 10-year projection models comparing **Dividend Reinvestment (DRIP)** vs **Cash Payout (No Reinvestment)**.")
                
                # Projections Math
                proj_data = []
                
                # Case A: Reinvestment (DRIP)
                shares_drip = selected_df["Shares to Buy"].tolist()
                prices_start = selected_df["Price"].tolist()
                div_rates_start = selected_df["Dividend Rate"].tolist()
                weights = [w / 100.0 for w in selected_df["Weight (%)"].tolist()]
                
                # Case B: No Reinvestment
                shares_no_reinvest = selected_df["Shares to Buy"].tolist()
                
                # Year 0 initial state
                proj_data.append({
                    "Year": 0,
                    "Portfolio Value (No Reinvestment)": required_total_inv,
                    "Annual Dividend (No Reinvestment)": selected_df["Expected Year 1 Dividend"].sum(),
                    "Portfolio Value (DRIP Reinvestment)": required_total_inv,
                    "Annual Dividend (DRIP Reinvestment)": selected_df["Expected Year 1 Dividend"].sum(),
                })
                
                for yr in range(1, 11):
                    # Stock prices and dividends increase
                    current_prices = [p * ((1 + exp_cap_appr / 100.0) ** yr) for p in prices_start]
                    current_div_rates = [d * ((1 + exp_div_growth / 100.0) ** yr) for d in div_rates_start]
                    
                    # 1. No Reinvestment
                    val_no_reinvest = sum(s * p for s, p in zip(shares_no_reinvest, current_prices))
                    div_no_reinvest = sum(s * d for s, d in zip(shares_no_reinvest, current_div_rates))
                    
                    # 2. DRIP Reinvestment
                    # Calculate dividend income for this year using previous year's shares
                    year_div_income = sum(s * d for s, d in zip(shares_drip, current_div_rates))
                    
                    # Reinvest this income into buying more shares at current prices
                    new_shares_bought = []
                    for i in range(len(shares_drip)):
                        reinvest_amt = weights[i] * year_div_income
                        price_per_share = current_prices[i]
                        new_shares = reinvest_amt / price_per_share if price_per_share > 0 else 0
                        new_shares_bought.append(new_shares)
                    
                    # Update shares
                    shares_drip = [s + ns for s, ns in zip(shares_drip, new_shares_bought)]
                    
                    # Portfolio Value is the sum of updated shares times current price
                    val_drip = sum(s * p for s, p in zip(shares_drip, current_prices))
                    # Next year's dividend rate * current shares
                    div_drip = sum(s * d for s, d in zip(shares_drip, current_div_rates))
                    
                    proj_data.append({
                        "Year": yr,
                        "Portfolio Value (No Reinvestment)": val_no_reinvest,
                        "Annual Dividend (No Reinvestment)": div_no_reinvest,
                        "Portfolio Value (DRIP Reinvestment)": val_drip,
                        "Annual Dividend (DRIP Reinvestment)": div_drip,
                    })
                    
                df_proj = pd.DataFrame(proj_data)
                
                # Display 5 and 10 year projection stats
                y5 = df_proj[df_proj["Year"] == 5].iloc[0]
                y10 = df_proj[df_proj["Year"] == 10].iloc[0]
                
                col_sum1, col_sum2 = st.columns(2)
                with col_sum1:
                    st.markdown("**Without Reinvesting Dividends (Cash Payout):**")
                    summary_payout = pd.DataFrame([
                        {"Timeframe": "Initial (Year 0)", "Portfolio Value": f"{cur}{required_total_inv:,.2f}", "Annual Dividend": f"{cur}{df_proj.loc[0, 'Annual Dividend (No Reinvestment)']:,.2f}"},
                        {"Timeframe": "Year 5", "Portfolio Value": f"{cur}{y5['Portfolio Value (No Reinvestment)']:,.2f}", "Annual Dividend": f"{cur}{y5['Annual Dividend (No Reinvestment)']:,.2f}"},
                        {"Timeframe": "Year 10", "Portfolio Value": f"{cur}{y10['Portfolio Value (No Reinvestment)']:,.2f}", "Annual Dividend": f"{cur}{y10['Annual Dividend (No Reinvestment)']:,.2f}"},
                    ])
                    st.dataframe(summary_payout, use_container_width=True, hide_index=True)
                with col_sum2:
                    st.markdown("**With DRIP Reinvestment (Compound Growth):**")
                    summary_drip = pd.DataFrame([
                        {"Timeframe": "Initial (Year 0)", "Portfolio Value": f"{cur}{required_total_inv:,.2f}", "Annual Dividend": f"{cur}{df_proj.loc[0, 'Annual Dividend (DRIP Reinvestment)']:,.2f}"},
                        {"Timeframe": "Year 5", "Portfolio Value": f"{cur}{y5['Portfolio Value (DRIP Reinvestment)']:,.2f}", "Annual Dividend": f"{cur}{y5['Annual Dividend (DRIP Reinvestment)']:,.2f}"},
                        {"Timeframe": "Year 10", "Portfolio Value": f"{cur}{y10['Portfolio Value (DRIP Reinvestment)']:,.2f}", "Annual Dividend": f"{cur}{y10['Annual Dividend (DRIP Reinvestment)']:,.2f}"},
                    ])
                    st.dataframe(summary_drip, use_container_width=True, hide_index=True)
                
                # Plotly Charts
                fig_val = go.Figure()
                fig_val.add_trace(go.Scatter(
                    x=df_proj["Year"], 
                    y=df_proj["Portfolio Value (DRIP Reinvestment)"],
                    mode='lines+markers',
                    name='DRIP Reinvestment (Compound)',
                    line=dict(color='#22c55e', width=3)
                ))
                fig_val.add_trace(go.Scatter(
                    x=df_proj["Year"], 
                    y=df_proj["Portfolio Value (No Reinvestment)"],
                    mode='lines+markers',
                    name='No Reinvestment (Cash Outflow)',
                    line=dict(color='#e94560', width=2, dash='dash')
                ))
                fig_val.update_layout(
                    title="Portfolio Value Projection (10 Years)",
                    xaxis_title="Years",
                    yaxis_title=f"Portfolio Value ({cur})",
                    template="plotly_dark",
                    margin=dict(l=20, r=20, t=40, b=20),
                    height=400,
                )
                
                fig_div = go.Figure()
                fig_div.add_trace(go.Scatter(
                    x=df_proj["Year"], 
                    y=df_proj["Annual Dividend (DRIP Reinvestment)"],
                    mode='lines+markers',
                    name='DRIP Reinvestment (Compound)',
                    line=dict(color='#3b82f6', width=3)
                ))
                fig_div.add_trace(go.Scatter(
                    x=df_proj["Year"], 
                    y=df_proj["Annual Dividend (No Reinvestment)"],
                    mode='lines+markers',
                    name='No Reinvestment (Cash Outflow)',
                    line=dict(color='#f59e0b', width=2, dash='dash')
                ))
                fig_div.update_layout(
                    title="Annual Dividend Income Projection (10 Years)",
                    xaxis_title="Years",
                    yaxis_title=f"Annual Dividend ({cur})",
                    template="plotly_dark",
                    margin=dict(l=20, r=20, t=40, b=20),
                    height=400,
                )
                
                st.plotly_chart(fig_val, use_container_width=True)
                st.plotly_chart(fig_div, use_container_width=True)
                
                # Highlight of reinvestment benefits
                drip_diff_val = y10['Portfolio Value (DRIP Reinvestment)'] - y10['Portfolio Value (No Reinvestment)']
                drip_diff_div = y10['Annual Dividend (DRIP Reinvestment)'] - y10['Annual Dividend (No Reinvestment)']
                
                st.success(f"💡 **Reinvestment Power:** In 10 years, choosing to **reinvest dividends (DRIP)** results in an extra **{cur}{drip_diff_val:,.2f}** in portfolio value and an additional **{cur}{drip_diff_div:,.2f}** in annual dividend income compared to withdrawing cash dividends!")

    elif app_mode == "Live Intelligence Report":
        ticker = resolve_ticker(raw_ticker, market_val)
        st.subheader(f"🔴 Live Intelligence: `{ticker}`")

        # Quick snapshot metrics
        try:
            snap = yf.Ticker(ticker).info
            cur = get_currency_symbol(ticker)
            col1, col2, col3, col4 = st.columns(4)
            price = snap.get('currentPrice') or snap.get('regularMarketPrice')
            prev_close = snap.get('previousClose')
            change_pct = ((price - prev_close) / prev_close * 100) if price and prev_close else None
            mktcap = snap.get('marketCap')
            mktcap_str = f"{cur}{mktcap/1e9:.1f}B" if mktcap else "N/A"
            rec = snap.get('recommendationKey', '').replace('_', ' ').title() or 'N/A'
            col1.metric("Price", f"{cur}{price:.2f}" if price else "N/A",
                        f"{change_pct:+.2f}%" if change_pct else None)
            col2.metric("Market Cap", mktcap_str)
            col3.metric("Analyst Consensus", rec)
            col4.metric("Sector", snap.get('sector', 'N/A'))
        except Exception:
            pass

        # Chart
        chart_fig = plot_candlestick(ticker, period="3mo")
        if chart_fig:
            st.plotly_chart(chart_fig, use_container_width=True)

        with st.form(key="live_intel_form"):
            user_query = st.text_area(
                "Focus Area (Optional)",
                value=f"Run a full live intelligence analysis for {ticker}. Assess whether the upcoming results are likely to beat or miss expectations.",
                height=80
            )
            run_live = st.form_submit_button(label="🔴 Run Live Intelligence Analysis", type="primary")

        if run_live:
            with st.status("🔴 Live Intelligence Agents at work...", expanded=True) as status:
                st.write("📡 Fetching earnings history & beat/miss record...")
                st.write("📊 Pulling analyst estimates & price targets...")
                st.write("📅 Scanning for upcoming catalysts & events...")
                st.write("🏦 Checking insider & institutional activity...")
                st.write("🏢 Gathering company operations intelligence...")
                st.write("🌐 Searching live web for strategic moves...")

                initial_state = {
                    "messages": [],
                    "mode": "live_intel",
                    "ticker": ticker,
                    "market": market_val,
                    "query": user_query,
                    "agents_to_call": [],
                    "agents_called": [],
                    "technical_analysis": None,
                    "fundamental_analysis": None,
                    "news_analysis": None,
                    "dividend_analysis": None,
                    "moat_analysis": None,
                    "comparison_analysis": None,
                    "screener_analysis": None,
                    "live_intel_analysis": None,
                    "final_report": None,
                    "company_name": None,
                    "current_price": None,
                    "error": None,
                }

                try:
                    result = research_graph.invoke(initial_state)
                    final_report = result.get("final_report", "")
                    live_intel_raw = result.get("live_intel_analysis", "")
                    company_name = result.get("company_name", ticker)
                    status.update(label="✅ Live Intelligence Complete!", state="complete", expanded=False)

                    # ── Verdict Banner ──────────────────────────────────────
                    verdict_color = "#22c55e"
                    verdict_icon = "✅"
                    verdict_text = "LIKELY TO BEAT"
                    report_lower = final_report.lower() if final_report else ""
                    if "likely to miss" in report_lower or "miss" in report_lower[:300]:
                        verdict_color = "#ef4444"
                        verdict_icon = "❌"
                        verdict_text = "LIKELY TO MISS"
                    elif "in-line" in report_lower or "in line" in report_lower:
                        verdict_color = "#f59e0b"
                        verdict_icon = "➖"
                        verdict_text = "LIKELY IN-LINE"

                    st.markdown(f"""
                    <div style='background: linear-gradient(135deg, #0f172a, #1e293b);
                        border-left: 5px solid {verdict_color};
                        border-radius: 10px; padding: 20px; margin: 16px 0;'>
                        <div style='font-size: 0.85rem; color: #94a3b8; margin-bottom: 4px;'>LIVE EARNINGS VERDICT</div>
                        <div style='font-size: 2rem; font-weight: 800; color: {verdict_color};'>{verdict_icon} {verdict_text}</div>
                        <div style='font-size: 0.9rem; color: #cbd5e1; margin-top: 6px;'>{company_name} ({ticker}) · {datetime.now().strftime("%b %d, %Y %H:%M")}</div>
                    </div>
                    """, unsafe_allow_html=True)

                    # ── Final Report ────────────────────────────────────────
                    st.markdown("### 📋 Live Intelligence Report")
                    st.write_stream(stream_report(final_report))

                    # ── Raw Intel Data ──────────────────────────────────────
                    with st.expander("🔬 Raw Live Intelligence Data (from agent tools)"):
                        if live_intel_raw:
                            st.markdown(live_intel_raw)
                        else:
                            st.info("No raw data available.")

                    # ── PDF Download ────────────────────────────────────────
                    st.markdown("---")
                    st.markdown("### 📥 Download Report")
                    try:
                        pdf_bytes = generate_pdf_report(final_report)
                        safe_ticker = ticker.replace('.', '_')
                        filename = f"live_intel_{safe_ticker}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
                        st.download_button(
                            label="📄 Download Live Intelligence PDF",
                            data=pdf_bytes,
                            file_name=filename,
                            mime="application/pdf",
                            type="primary"
                        )
                    except Exception as pdf_err:
                        st.warning(f"PDF generation failed: {pdf_err}")

                except Exception as e:
                    status.update(label="❌ Live Intelligence Failed", state="error", expanded=True)
                    st.error(f"Pipeline failed: {e}")
    elif app_mode == "Live News Report":
        ticker = resolve_ticker(raw_ticker, market_val)
        st.subheader(f"📰 Live News Report: `{ticker}`")

        # Quick snapshot metrics
        try:
            snap = yf.Ticker(ticker).info
            cur = get_currency_symbol(ticker)
            col1, col2, col3, col4 = st.columns(4)
            price = snap.get('currentPrice') or snap.get('regularMarketPrice')
            prev_close = snap.get('previousClose')
            change_pct = ((price - prev_close) / prev_close * 100) if price and prev_close else None
            mktcap = snap.get('marketCap')
            mktcap_str = f"{cur}{mktcap/1e9:.1f}B" if mktcap else "N/A"
            rec = snap.get('recommendationKey', '').replace('_', ' ').title() or 'N/A'
            col1.metric("Price", f"{cur}{price:.2f}" if price else "N/A",
                        f"{change_pct:+.2f}%" if change_pct else None)
            col2.metric("Market Cap", mktcap_str)
            col3.metric("Analyst Consensus", rec)
            col4.metric("Sector", snap.get('sector', 'N/A'))
        except Exception:
            pass

        # Chart
        chart_fig = plot_candlestick(ticker, period="3mo")
        if chart_fig:
            st.plotly_chart(chart_fig, use_container_width=True)

        with st.form(key="live_news_report_form"):
            user_query = st.text_area(
                "Focus Area (Optional)",
                value=f"Run a live news analysis for {ticker}. Assess what breaking news or sentiment shifts are likely to impact the stock in the next 1-3 days.",
                height=80
            )
            run_live_news = st.form_submit_button(label="📰 Run Live News Report Analysis", type="primary")

        if run_live_news:
            with st.status("📰 Live News Report Agents at work...", expanded=True) as status:
                st.write("📰 Fetching breaking news & real-time sentiment...")
                st.write("📈 Analyzing news-driven catalysts & events...")
                st.write("🔍 Scanning trending topics & social signals...")
                st.write("⚡ Assessing live event impact on price action...")
                st.write("🌐 Searching live web for news verification...")

                initial_state = {
                    "messages": [],
                    "mode": "live_news",
                    "ticker": ticker,
                    "market": market_val,
                    "query": user_query,
                    "agents_to_call": [],
                    "agents_called": [],
                    "technical_analysis": None,
                    "fundamental_analysis": None,
                    "news_analysis": None,
                    "dividend_analysis": None,
                    "moat_analysis": None,
                    "comparison_analysis": None,
                    "screener_analysis": None,
                    "live_intel_analysis": None,
                    "live_news_analysis": None,
                    "final_report": None,
                    "company_name": None,
                    "current_price": None,
                    "error": None,
                }

                try:
                    result = research_graph.invoke(initial_state)
                    final_report = result.get("final_report", "")
                    live_news_raw = result.get("live_news_analysis", "")
                    company_name = result.get("company_name", ticker)
                    status.update(label="✅ Live News Report Complete!", state="complete", expanded=False)

                    # ── Verdict Banner ──────────────────────────────────────
                    verdict_color = "#10b981"
                    verdict_icon = "📈"
                    verdict_text = "LIKELY TO OUTPERFORM"
                    report_lower = final_report.lower() if final_report else ""
                    if "likely to underperform" in report_lower or "underperform" in report_lower[:300]:
                        verdict_color = "#ef4444"
                        verdict_icon = "📉"
                        verdict_text = "LIKELY TO UNDERPERFORM"
                    elif "trade in-line" in report_lower or "in-line" in report_lower or "trade in line" in report_lower:
                        verdict_color = "#f59e0b"
                        verdict_icon = "➡️"
                        verdict_text = "LIKELY TO TRADE IN-LINE"

                    st.markdown(f"""
                    <div style='background: linear-gradient(135deg, #0f172a, #1e293b);
                        border-left: 5px solid {verdict_color};
                        border-radius: 10px; padding: 20px; margin: 16px 0;'>
                        <div style='font-size: 0.85rem; color: #94a3b8; margin-bottom: 4px;'>LIVE NEWS VERDICT</div>
                        <div style='font-size: 2rem; font-weight: 800; color: {verdict_color};'>{verdict_icon} {verdict_text}</div>
                        <div style='font-size: 0.9rem; color: #cbd5e1; margin-top: 6px;'>{company_name} ({ticker}) · {datetime.now().strftime("%b %d, %Y %H:%M")}</div>
                    </div>
                    """, unsafe_allow_html=True)

                    # ── Final Report ────────────────────────────────────────
                    st.markdown("### 📋 Live News Report")
                    st.write_stream(stream_report(final_report))

                    # ── Raw News Data ───────────────────────────────────────
                    with st.expander("📰 Raw Live News Report Data (from agent tools)"):
                        if live_news_raw:
                            st.markdown(live_news_raw)
                        else:
                            st.info("No raw data available.")

                    # ── PDF Download ────────────────────────────────────────
                    st.markdown("---")
                    st.markdown("### 📥 Download Report")
                    try:
                        pdf_bytes = generate_pdf_report(final_report)
                        safe_ticker = ticker.replace('.', '_')
                        filename = f"live_news_report_{safe_ticker}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
                        st.download_button(
                            label="📄 Download Live News Report PDF",
                            data=pdf_bytes,
                            file_name=filename,
                            mime="application/pdf",
                            type="primary"
                        )
                    except Exception as pdf_err:
                        st.warning(f"PDF generation failed: {pdf_err}")

                except Exception as e:
                    status.update(label="❌ Live News Intelligence Failed", state="error", expanded=True)
                    st.error(f"Pipeline failed: {e}")

    elif app_mode == "Family Portfolio Review":
        st.subheader("💼 Family Portfolio Analyzer & Review")
        
        # File uploader
        uploaded_file = st.file_uploader("Upload Family Holdings Excel File", type=["xlsx", "xls"])
        
        if uploaded_file is not None:
            with st.spinner("Analyzing spreadsheet data..."):
                try:
                    holdings_df, report_df = parse_holdings_excel(uploaded_file)
                    portfolio = aggregate_portfolio_data(holdings_df, report_df)
                except Exception as parse_err:
                    st.error(f"Failed to parse holdings file: {parse_err}")
                    portfolio = None
        else:
            st.info("👈 Please upload your family holdings Excel file (`.xlsx` or `.xls`) to begin the portfolio analysis and review.")
            portfolio = None
            
        if portfolio:
            # 1. Metric Cards
            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
            with col_m1:
                st.metric("Total Portfolio Value", f"₹{portfolio['total_market_value']:,.2f}")
            with col_m2:
                st.metric("Total Invested Cost", f"₹{portfolio['total_invested']:,.2f}")
            with col_m3:
                gain_val = portfolio['total_gain']
                gain_pct = portfolio['total_gain_pct']
                st.metric("Total Gain/Loss", f"₹{gain_val:+,.2f}", f"{gain_pct:+.2f}%")
            with col_m4:
                # Liquid assets MV vs total MV
                liquid_mv = (
                    portfolio['asset_class_mv_map'].get('Equity', 0) +
                    portfolio['asset_class_mv_map'].get('Global Equity', 0) +
                    portfolio['asset_class_mv_map'].get('Gold', 0) +
                    portfolio['asset_class_mv_map'].get('Silver', 0) +
                    portfolio['asset_class_mv_map'].get('Liquid', 0)
                )
                liquid_pct = (liquid_mv / portfolio['total_market_value'] * 100) if portfolio['total_market_value'] > 0 else 0
                st.metric("Liquid Net Worth %", f"{liquid_pct:.1f}%")
                
            tab_ac, tab_stock, tab_ai = st.tabs([
                "📊 Asset Allocation",
                "📈 Stock Holdings (Deep Dive)",
                "🤖 AI Portfolio Review"
            ])
            
            with tab_ac:
                st.markdown("### 📊 Asset Class Distribution")
                st.write("Allocation of all family assets including real estate, retirement funds, vehicle, and cash.")
                
                col_chart, col_table = st.columns([3, 2])
                
                with col_chart:
                    # Plotly pie chart of asset classes
                    df_ac = portfolio['asset_class_df']
                    fig_ac = go.Figure(data=[go.Pie(
                        labels=df_ac['Asset Class'],
                        values=df_ac['Market Value'],
                        hole=.3,
                        textinfo='percent+label',
                        marker=dict(colors=['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#6366f1', '#14b8a6', '#f43f5e'])
                    )])
                    fig_ac.update_layout(
                        template="plotly_dark",
                        margin=dict(l=0, r=0, t=30, b=0),
                        height=400,
                        showlegend=False
                    )
                    st.plotly_chart(fig_ac, use_container_width=True)
                    
                with col_table:
                    # Cleaned table representation
                    st.markdown("#### Allocation Summary")
                    df_ac_disp = df_ac.copy()
                    df_ac_disp['Market Value'] = df_ac_disp['Market Value'].apply(lambda x: f"₹{x:,.2f}")
                    df_ac_disp['Invested'] = df_ac_disp['Invested'].apply(lambda x: f"₹{x:,.2f}")
                    df_ac_disp['Gain/Loss'] = df_ac_disp['Gain/Loss'].apply(lambda x: f"₹{x:+,.2f}")
                    df_ac_disp['Gain/Loss %'] = df_ac_disp['Gain/Loss %'].apply(lambda x: f"{x:.2f}%")
                    df_ac_disp['Allocation (%)'] = df_ac_disp['Allocation (%)'].apply(lambda x: f"{x:.2f}%")
                    st.dataframe(df_ac_disp, use_container_width=True, hide_index=True)
                    
                # Liquid vs Illiquid assets callout
                st.markdown("---")
                col_l1, col_l2 = st.columns(2)
                with col_l1:
                    st.info(f"💧 **Liquid Assets:** ₹{liquid_mv:,.2f} ({liquid_pct:.1f}%) — Stock, Global Stock, Gold, Silver, Savings Cash.")
                with col_l2:
                    illiquid_mv = portfolio['total_market_value'] - liquid_mv
                    illiquid_pct = 100 - liquid_pct
                    st.warning(f"🏠 **Illiquid Assets:** ₹{illiquid_mv:,.2f} ({illiquid_pct:.1f}%) — Real Estate, Retirement (EPF), Vehicle, ESOPs.")
                    
            with tab_stock:
                st.markdown("### 📈 Direct Equity & Market Holdings")
                st.write("Detailed view of stock market investments (Indian stocks, US stocks, Gold and Silver funds).")
                
                df_h = portfolio['clean_holdings_df']
                
                if df_h is not None and not df_h.empty:
                    # Charts row
                    col_c1, col_c2 = st.columns(2)
                    
                    with col_c1:
                        # Cap-size distribution
                        df_cat = portfolio['category_df']
                        fig_cat = go.Figure(data=[go.Bar(
                            x=df_cat['Category'],
                            y=df_cat['Market Value'],
                            marker_color='#3b82f6',
                            text=[f"{val:.1f}%" for val in df_cat['Allocation (%)']],
                            textposition='auto',
                        )])
                        fig_cat.update_layout(
                            title="Cap-Size Allocation (Market Value)",
                            template="plotly_dark",
                            yaxis_title="Market Value (₹)",
                            xaxis_title="Category",
                            margin=dict(l=20, r=20, t=40, b=20),
                            height=300
                        )
                        st.plotly_chart(fig_cat, use_container_width=True)
                        
                    with col_c2:
                        # Broker distribution
                        df_brk = portfolio['broker_df']
                        fig_brk = go.Figure(data=[go.Pie(
                            labels=df_brk['Broker'],
                            values=df_brk['Market Value'],
                            hole=.3,
                            textinfo='percent+label',
                            marker=dict(colors=['#10b981', '#f59e0b'])
                        )])
                        fig_brk.update_layout(
                            title="Broker / Custody Split",
                            template="plotly_dark",
                            margin=dict(l=20, r=20, t=40, b=20),
                            height=300,
                            showlegend=False
                        )
                        st.plotly_chart(fig_brk, use_container_width=True)
                        
                    # Top Holdings Horizontal Bar Chart
                    st.markdown("#### Top 10 Stock Holdings by Market Value")
                    df_top = portfolio['top_holdings_df']
                    fig_top = go.Figure(data=[go.Bar(
                        y=df_top['Investment'],
                        x=df_top['Market Value'],
                        orientation='h',
                        marker_color='#10b981',
                        text=[f"₹{val:,.0f}" for val in df_top['Market Value']],
                        textposition='inside',
                    )])
                    fig_top.update_layout(
                        template="plotly_dark",
                        margin=dict(l=20, r=20, t=30, b=20),
                        height=350,
                        yaxis=dict(autorange="reversed"),
                        xaxis_title="Market Value (₹)"
                    )
                    st.plotly_chart(fig_top, use_container_width=True)
                    
                    # Search and filters for individual holdings table
                    st.markdown("#### 🔍 Filter Stock Holdings")
                    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
                    
                    with col_f1:
                        unique_ac = ["All"] + sorted(list(df_h['Asset Class'].unique()))
                        f_ac = st.selectbox("Filter Asset Class", unique_ac)
                    with col_f2:
                        unique_cat = ["All"] + sorted(list(df_h['Category'].unique()))
                        f_cat = st.selectbox("Filter Category", unique_cat)
                    with col_f3:
                        unique_brk = ["All"] + sorted(list(df_h['Broker'].unique()))
                        f_brk = st.selectbox("Filter Broker", unique_brk)
                    with col_f4:
                        unique_mem = ["All"] + sorted(list(df_h['First Name'].unique()))
                        f_mem = st.selectbox("Filter Family Member", unique_mem)
                        
                    search_term = st.text_input("Search Investment Name", placeholder="e.g. Reliance, Apple...")
                    
                    # Apply filters
                    filtered_df = df_h.copy()
                    if f_ac != "All":
                        filtered_df = filtered_df[filtered_df['Asset Class'] == f_ac]
                    if f_cat != "All":
                        filtered_df = filtered_df[filtered_df['Category'] == f_cat]
                    if f_brk != "All":
                        filtered_df = filtered_df[filtered_df['Broker'] == f_brk]
                    if f_mem != "All":
                        filtered_df = filtered_df[filtered_df['First Name'] == f_mem]
                    if search_term:
                        filtered_df = filtered_df[filtered_df['Investment'].str.contains(search_term, case=False, na=False)]
                        
                    # Format columns for display
                    df_h_disp = filtered_df.copy()
                    cols_to_show = ["Investment", "Asset Class", "Category", "Broker", "Total Units", "Invested Amount", "Market Value", "Total Gain/Loss (INR)", "Total Gain/Loss (%)"]
                    
                    cols_to_show = [c for c in cols_to_show if c in df_h_disp.columns]
                    df_h_disp = df_h_disp[cols_to_show]
                    
                    df_h_disp['Invested Amount'] = df_h_disp['Invested Amount'].apply(lambda x: f"₹{x:,.2f}")
                    df_h_disp['Market Value'] = df_h_disp['Market Value'].apply(lambda x: f"₹{x:,.2f}")
                    if 'Total Gain/Loss (INR)' in df_h_disp.columns:
                        df_h_disp['Total Gain/Loss (INR)'] = df_h_disp['Total Gain/Loss (INR)'].apply(lambda x: f"₹{x:+,.2f}")
                    if 'Total Gain/Loss (%)' in df_h_disp.columns:
                        df_h_disp['Total Gain/Loss (%)'] = df_h_disp['Total Gain/Loss (%)'].apply(lambda x: f"{x:+.2f}%")
                    if 'Total Units' in df_h_disp.columns:
                        df_h_disp['Total Units'] = df_h_disp['Total Units'].apply(lambda x: f"{x:,.4f}")
                        
                    st.dataframe(df_h_disp, use_container_width=True, hide_index=True)
                else:
                    st.warning("No detailed holdings data found in the spreadsheet.")
                    
            with tab_ai:
                st.markdown("### 🤖 Agentic Portfolio Review")
                st.write("Let the Portfolio Analyst Agent audit your asset allocation, evaluate risks, and draft actionable strategic recommendations.")
                
                with st.form(key="portfolio_agent_form"):
                    focus_query = st.text_area(
                        "Review Focus Area (Optional)",
                        placeholder="e.g. Assess my exposure to small caps, critique my US vs. India equity allocation split, and recommend rebalancing steps.",
                        height=100
                    )
                    run_review = st.form_submit_button("🧠 Generate Agentic Portfolio Review", type="primary", use_container_width=True)
                    
                if run_review:
                    with st.status("🧠 Portfolio Analyst Agent at work...", expanded=True) as status:
                        st.write("📊 Digesting total portfolio allocations...")
                        st.write("🔍 Auditing stock cap-size categories & concentrations...")
                        st.write("⚖️ Evaluating Indian vs. Global equity balance...")
                        st.write("🏢 Evaluating liquid vs. fixed assets...")
                        st.write("🤖 Modeling rebalancing recommendations...")
                        
                        try:
                            review_report = run_portfolio_review_agent(portfolio, focus_query)
                            status.update(label="✅ Portfolio Review Complete!", state="complete", expanded=False)
                            
                            st.markdown(review_report)
                            
                            st.session_state["portfolio_review_report"] = review_report
                        except Exception as e:
                            status.update(label="❌ Review Failed", state="error", expanded=True)
                            st.error(f"Failed to generate review: {e}")
                            
                if "portfolio_review_report" in st.session_state and st.session_state["portfolio_review_report"]:
                    st.markdown("---")
                    st.markdown("### 📥 Download Portfolio Review Report")
                    try:
                        pdf_bytes = generate_pdf_report(st.session_state["portfolio_review_report"])
                        filename = f"portfolio_review_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
                        st.download_button(
                            label="📄 Download Portfolio Review PDF",
                            data=pdf_bytes,
                            file_name=filename,
                            mime="application/pdf",
                            type="primary"
                        )
                    except Exception as pdf_err:
                        st.warning(f"PDF generation failed: {pdf_err}")

    else:
        # Existing logic for agents
        # Chat / Query input
        query_map = {
            "Full Deep Dive (Tech, Fund, News)": f"Provide a comprehensive investment research report for {ticker} including technicals, fundamentals, and recent news.",
            "Technical Analysis Only": f"Focus only on technical analysis and price action for {ticker}.",
            "Fundamental Analysis Only": f"Focus only on fundamental analysis, valuation, and financials for {ticker}.",
            "Dividend Yield Report": f"Provide a detailed dividend yield and safety report for {ticker}.",
            "Economic Moat Report": f"Analyze the economic moat and competitive advantages of {ticker}.",
            "Comparison Report": f"Compare these stocks side-by-side: {ticker}.",
            "Thematic Screener Report": f"Find stocks matching this theme: '{ticker}' and evaluate their moat and technicals."
        }
        
        default_query = query_map.get(depth, f"Analyze {ticker}")
        
        with st.form(key="research_form"):
            user_query = st.text_area("Custom Query (Optional)", value=default_query, height=100)
            submit_button = st.form_submit_button(label="🚀 Run Agentic Research")

        if submit_button:
            with st.status("🧠 Agents at work...", expanded=True) as status:
                
                # Map UI mode to internal state mode
                mode_map = {
                    "Single Stock Research": "single",
                    "Compare Stocks": "compare",
                    "Thematic Screener": "screener"
                }
                internal_mode = mode_map.get(app_mode, "single")

                initial_state = {
                    "messages": [],
                    "mode": internal_mode,
                    "ticker": ticker,
                    "market": market_val,
                    "query": user_query,
                    "agents_to_call": [],
                    "agents_called": [],
                    "technical_analysis": None,
                    "fundamental_analysis": None,
                    "news_analysis": None,
                    "dividend_analysis": None,
                    "moat_analysis": None,
                    "comparison_analysis": None,
                    "screener_analysis": None,
                    "final_report": None,
                    "company_name": None,
                    "current_price": None,
                    "error": None,
                }
                
                # Since LangGraph invocation can be opaque, we'll run it and display the final result.
                # In a more advanced UI, we'd use graph.stream() to show node-by-node progress.
                try:
                    st.write("Routing query via Supervisor...")
                    result = research_graph.invoke(initial_state)
                    
                    agents_run = result.get('agents_called', [])
                    st.write(f"Specialists consulted: {', '.join(agents_run).title()}")
                    
                    st.write("Synthesizer drafting final report...")
                    
                    final_report = result.get("final_report", "No report generated.")
                    status.update(label="✅ Research Complete!", state="complete", expanded=False)
                    
                    st.markdown("### 📋 Final Research Report")
                    st.write_stream(stream_report(final_report))
                    
                    with st.expander("Raw Analyst Data"):
                        if "technical" in agents_run:
                            st.markdown(result.get("technical_analysis", ""))
                        if "fundamental" in agents_run:
                            st.markdown(result.get("fundamental_analysis", ""))
                        if "news" in agents_run:
                            st.markdown(result.get("news_analysis", ""))
                        if "dividend" in agents_run:
                            st.markdown(result.get("dividend_analysis", ""))
                        if "moat" in agents_run:
                            st.markdown(result.get("moat_analysis", ""))
                        if "comparison" in agents_run:
                            st.markdown(result.get("comparison_analysis", ""))
                        if "screener" in agents_run:
                            st.markdown(result.get("screener_analysis", ""))
                            
                except Exception as e:
                    status.update(label="❌ Error in Research", state="error", expanded=True)
                    st.error(f"Pipeline failed: {e}")
