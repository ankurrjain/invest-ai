"""
Streamlit UI for InvestAI.
"""
import streamlit as st
import plotly.graph_objects as go
import yfinance as yf
import pandas as pd
from invest_ai.agents.graph import research_graph
from invest_ai.utils.ticker import resolve_ticker, get_currency_symbol
from invest_ai.utils.dashboards import (
    get_us_etf_holdings,
    get_nifty_50_constituents,
    get_nifty_next_50_constituents,
    get_bank_nifty_constituents,
    get_fii_dii_holdings,
    get_trending_stocks
)

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
        background-color: #1A202C;
        border-right: 1px solid #2D3748;
    }
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
    
    app_mode = st.radio("Mode", ["Single Stock Research", "Compare Stocks", "Thematic Screener", "Dashboards"])
    
    market = st.radio("Target Market", ["India (NSE/BSE)", "US (NYSE/NASDAQ)"])
    market_val = "india" if "India" in market else "us"
    
    st.markdown("### 🔍 Research Target")
    
    if app_mode == "Single Stock Research":
        raw_ticker = st.text_input("Enter Ticker Symbol", placeholder="e.g. RELIANCE or AAPL").upper()
        depth = st.selectbox("Analysis Depth", [
            "Full Deep Dive (Tech, Fund, News)",
            "Technical Analysis Only",
            "Fundamental Analysis Only",
            "News & Sentiment Only",
            "Dividend Yield Report",
            "Economic Moat Report"
        ])
    elif app_mode == "Compare Stocks":
        raw_ticker = st.text_input("Enter Tickers (comma-separated)", placeholder="e.g. AAPL, MSFT, GOOGL").upper()
        depth = "Comparison Report"
    elif app_mode == "Dashboards":
        st.markdown("Explore comprehensive dashboards for ETFs and stock trends.")
        raw_ticker = "Dashboards"  # Dummy value to pass the 'if not raw_ticker' check
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

    else:
        # Existing logic for agents
        # Chat / Query input
        query_map = {
            "Full Deep Dive (Tech, Fund, News)": f"Provide a comprehensive investment research report for {ticker} including technicals, fundamentals, and recent news.",
            "Technical Analysis Only": f"Focus only on technical analysis and price action for {ticker}.",
            "Fundamental Analysis Only": f"Focus only on fundamental analysis, valuation, and financials for {ticker}.",
            "News & Sentiment Only": f"Focus only on recent news and market sentiment for {ticker}.",
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
