"""
Streamlit UI for InvestAI.
"""
import streamlit as st
import plotly.graph_objects as go
import yfinance as yf
import pandas as pd
from datetime import datetime
from invest_ai.agents.graph import research_graph
from invest_ai.utils.ticker import resolve_ticker, get_currency_symbol
from invest_ai.utils.pdf import generate_pdf_report
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
    
    app_mode = st.radio("Mode", ["Single Stock Research", "Compare Stocks", "Thematic Screener", "Dashboards", "Dividend Target Planner", "Live Intelligence Report", "Live News Report"])
    
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
