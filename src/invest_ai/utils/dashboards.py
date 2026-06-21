import pandas as pd
import yfinance as yf
import requests
from bs4 import BeautifulSoup
import streamlit as st
import io

@st.cache_data(ttl=3600)
def get_us_etf_holdings(symbol: str) -> pd.DataFrame:
    try:
        ticker = yf.Ticker(symbol)
        if not hasattr(ticker, 'funds_data') or ticker.funds_data is None or ticker.funds_data.top_holdings is None:
            return pd.DataFrame()
        
        df = ticker.funds_data.top_holdings.copy()
        
        # Enrich with live data (Price, P/E) to make it professional
        prices = []
        pes = []
        for sym in df.index:
            try:
                t = yf.Ticker(sym)
                info = t.info
                prices.append(info.get('currentPrice', info.get('regularMarketPrice', 'N/A')))
                pes.append(info.get('trailingPE', 'N/A'))
            except Exception:
                prices.append('N/A')
                pes.append('N/A')
                
        df['Live Price'] = prices
        df['P/E Ratio'] = pes
        
        df = df.reset_index()
        return df
    except Exception as e:
        print(f"Error fetching holdings for {symbol}: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=86400)
def get_nifty_50_constituents() -> pd.DataFrame:
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'}
        url = "https://en.wikipedia.org/wiki/NIFTY_50"
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f"Nifty 50 fetch failed with status {response.status_code}")
            return pd.DataFrame()
        tables = pd.read_html(io.StringIO(response.text))
        # Find the table that contains the constituents
        for df in tables:
            if 'Symbol' in df.columns and ('Company Name' in df.columns or 'Company name' in df.columns):
                name_col = 'Company Name' if 'Company Name' in df.columns else 'Company name'
                # Find sector column which might have reference links like Sector[15]
                sector_col = next((col for col in df.columns if 'Sector' in col), None)
                if sector_col:
                    return df[[name_col, 'Symbol', sector_col]].rename(columns={name_col: 'Company Name', sector_col: 'Sector'})
                return df[[name_col, 'Symbol']].rename(columns={name_col: 'Company Name'})
        print("Nifty 50 constituents table not found.")
        return pd.DataFrame()
    except Exception as e:
        print(f"Error fetching Nifty 50: {type(e).__name__}")
        return pd.DataFrame()

@st.cache_data(ttl=86400)
def get_nifty_next_50_constituents() -> pd.DataFrame:
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'}
        url = "https://en.wikipedia.org/wiki/NIFTY_Next_50"
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f"Nifty Next 50 fetch failed with status {response.status_code}")
            return pd.DataFrame()
        tables = pd.read_html(io.StringIO(response.text))
        for df in tables:
            if 'Symbol' in df.columns and ('Company Name' in df.columns or 'Company name' in df.columns):
                name_col = 'Company Name' if 'Company Name' in df.columns else 'Company name'
                sector_col = next((col for col in df.columns if 'Sector' in col), None)
                if sector_col:
                    return df[[name_col, 'Symbol', sector_col]].rename(columns={name_col: 'Company Name', sector_col: 'Sector'})
                return df[[name_col, 'Symbol']].rename(columns={name_col: 'Company Name'})
        print("Nifty Next 50 constituents table not found.")
        return pd.DataFrame()
    except Exception as e:
        print(f"Error fetching Nifty Next 50: {type(e).__name__}")
        return pd.DataFrame()

@st.cache_data(ttl=86400)
def get_bank_nifty_constituents() -> pd.DataFrame:
    # Bank Nifty constituents are 12 highly liquid Indian banks.
    # Wikipedia lacks a dedicated page for this, so we use the canonical list.
    data = [
        {"Company Name": "HDFC Bank", "Symbol": "HDFCBANK", "Sector": "Financial Services"},
        {"Company Name": "ICICI Bank", "Symbol": "ICICIBANK", "Sector": "Financial Services"},
        {"Company Name": "State Bank of India", "Symbol": "SBIN", "Sector": "Financial Services"},
        {"Company Name": "Axis Bank", "Symbol": "AXISBANK", "Sector": "Financial Services"},
        {"Company Name": "Kotak Mahindra Bank", "Symbol": "KOTAKBANK", "Sector": "Financial Services"},
        {"Company Name": "IndusInd Bank", "Symbol": "INDUSINDBK", "Sector": "Financial Services"},
        {"Company Name": "Bank of Baroda", "Symbol": "BANKBARODA", "Sector": "Financial Services"},
        {"Company Name": "Punjab National Bank", "Symbol": "PNB", "Sector": "Financial Services"},
        {"Company Name": "Federal Bank", "Symbol": "FEDERALBNK", "Sector": "Financial Services"},
        {"Company Name": "IDFC First Bank", "Symbol": "IDFCFIRSTB", "Sector": "Financial Services"},
        {"Company Name": "AU Small Finance Bank", "Symbol": "AUBANK", "Sector": "Financial Services"},
        {"Company Name": "Bandhan Bank", "Symbol": "BANDHANBNK", "Sector": "Financial Services"},
    ]
    return pd.DataFrame(data)

@st.cache_data(ttl=3600)
def get_fii_dii_holdings(symbols: list) -> pd.DataFrame:
    data = []
    for sym in symbols:
        try:
            ticker = yf.Ticker(sym)
            info = ticker.info
            inst_hold = info.get('heldPercentInstitutions', 0)
            if inst_hold is not None:
                inst_hold = inst_hold * 100
            else:
                inst_hold = 0
            
            data.append({
                'Symbol': sym,
                'Name': info.get('shortName', sym),
                'Institutional Holding (%)': round(inst_hold, 2)
            })
        except Exception:
            continue
    df = pd.DataFrame(data)
    if not df.empty:
        df = df.sort_values('Institutional Holding (%)', ascending=False)
    return df

@st.cache_data(ttl=3600)
def get_trending_stocks(symbols: list) -> pd.DataFrame:
    data = []
    for sym in symbols:
        try:
            ticker = yf.Ticker(sym)
            hist = ticker.history(period="2d")
            if len(hist) >= 2:
                prev_close = hist['Close'].iloc[0]
                curr_close = hist['Close'].iloc[1]
                pct_change = ((curr_close - prev_close) / prev_close) * 100
                data.append({
                    'Symbol': sym,
                    'Price': round(curr_close, 2),
                    '% Change': round(pct_change, 2),
                    'Volume': hist['Volume'].iloc[1]
                })
        except Exception:
            continue
    df = pd.DataFrame(data)
    if not df.empty:
        df = df.sort_values('% Change', ascending=False)
    return df

@st.cache_data(ttl=3600)
def get_dividend_candidate_data(market: str) -> pd.DataFrame:
    import concurrent.futures
    if market == "us":
        candidates = [
            "SCHD", "JEPI", "T", "VZ", "MO", "PM", "O", "ABBV", "JNJ", "PG",
            "KO", "PEP", "XOM", "CVX", "MAIN", "WPC", "IBM", "MMM", "PFE", "NEE",
            "EPD", "BTI", "LMT", "AVGO", "ENB", "ET", "FRT", "ADC"
        ]
    else: # india
        candidates = [
            "COALINDIA.NS", "RECLTD.NS", "PFC.NS", "ONGC.NS", "IOC.NS", "BPCL.NS",
            "VEDL.NS", "HINDZINC.NS", "ITC.NS", "TCS.NS", "INFY.NS", "POWERGRID.NS",
            "GAIL.NS", "NTPC.NS", "HCLTECH.NS", "OIL.NS", "NMDC.NS", "SJVN.NS",
            "NHPC.NS", "IRFC.NS", "HUDCO.NS", "PETRONET.NS", "MUTHOOTFIN.NS",
            "TATASTEEL.NS", "HINDALCO.NS"
        ]
        
    def fetch_data(symbol):
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            # extract yield
            dy = info.get("dividendYield")
            if dy is not None:
                dy = round(dy * 100, 2)
            else:
                dy = 0.0
                
            # extract payout ratio
            pr = info.get("payoutRatio")
            if pr is not None:
                pr = round(pr * 100, 2)
            else:
                pr = 0.0
                
            price = info.get("currentPrice") or info.get("regularMarketPrice") or 0.0
            div_rate = info.get("dividendRate") or 0.0
            
            # Fallback if yield is 0 but rate and price exist
            if dy == 0.0 and div_rate > 0 and price > 0:
                dy = round((div_rate / price) * 100, 2)
                
            # If rate is 0 but yield and price exist
            if div_rate == 0.0 and dy > 0 and price > 0:
                div_rate = round((dy / 100) * price, 2)

            return {
                "Symbol": symbol,
                "Name": info.get("longName") or info.get("shortName") or symbol,
                "Price": price,
                "Yield (%)": dy,
                "Payout Ratio (%)": pr,
                "Dividend Rate": div_rate,
                "Sector": info.get("sector", "N/A"),
                "Industry": info.get("industry", "N/A")
            }
        except Exception:
            return None

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fetch_data, sym): sym for sym in candidates}
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res is not None and res["Price"] > 0:
                results.append(res)
                
    df = pd.DataFrame(results)
    # Sort by yield descending
    if not df.empty:
        df = df.sort_values("Yield (%)", ascending=False).reset_index(drop=True)
    return df
