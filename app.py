"""
Streamlit UI for InvestAI.
"""
import streamlit as st
import plotly.graph_objects as go
import yfinance as yf
from invest_ai.agents.graph import research_graph
from invest_ai.utils.ticker import resolve_ticker, get_currency_symbol

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
    
    app_mode = st.radio("Mode", ["Single Stock Research", "Compare Stocks", "Thematic Screener"])
    
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
    else:
        ticker = raw_ticker
        st.subheader(f"Screening Theme: `{ticker}`")
    
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
