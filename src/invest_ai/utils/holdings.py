"""
Excel parser and aggregator for holdings-family xls/xlsx structures.
"""
import pandas as pd
import numpy as np

def clean_num_val(val):
    """Sanitize formats (commas, percentages, etc.) to float."""
    if pd.isnull(val):
        return 0.0
    val_str = str(val).replace(",", "").replace("%", "").strip()
    if val_str in ("-", "", "None", "nan"):
        return 0.0
    try:
        return float(val_str)
    except ValueError:
        return 0.0

def parse_holdings_excel(file_path_or_bytes):
    """
    Scans Excel sheets, identifies holdings sheet and report sheet dynamically,
    parses them, and returns (holdings_df, report_df).
    """
    xls = pd.ExcelFile(file_path_or_bytes)
    holdings_df = None
    report_df = None
    
    for sheet_name in xls.sheet_names:
        # Read first 15 rows without header to inspect
        df_check = pd.read_excel(xls, sheet_name=sheet_name, header=None, nrows=15)
        
        # Look for header row containing key fields
        header_row_idx = None
        for idx, row in df_check.iterrows():
            row_vals = [str(x).strip().lower() for x in row.values if pd.notnull(x)]
            if 'source_holding_id' in row_vals or ('investment' in row_vals and 'invested amount' in row_vals):
                header_row_idx = idx
                break
        
        if header_row_idx is not None:
            # Detailed holdings sheet
            holdings_df = pd.read_excel(xls, sheet_name=sheet_name, header=header_row_idx)
            # Ensure key fields are not null
            holdings_df = holdings_df.dropna(subset=['Investment'])
        elif sheet_name.lower() == 'report' or 'report' in sheet_name.lower():
            # Summary report sheet
            df_check_report = pd.read_excel(xls, sheet_name=sheet_name, header=None, nrows=15)
            header_idx = 0
            for idx, row in df_check_report.iterrows():
                row_vals = [str(x).strip().lower() for x in row.values if pd.notnull(x)]
                if 'category' in row_vals or 'row labels' in row_vals:
                    header_idx = idx
                    break
            report_df = pd.read_excel(xls, sheet_name=sheet_name, header=header_idx)
            
    # Fallback to sheet indices if not found dynamically
    if holdings_df is None and len(xls.sheet_names) > 0:
        holdings_df = pd.read_excel(xls, sheet_name=0, header=5)
    if report_df is None and len(xls.sheet_names) > 1:
        report_df = pd.read_excel(xls, sheet_name=1, header=2)
        
    return holdings_df, report_df

def aggregate_portfolio_data(holdings_df, report_df):
    """
    Processes holdings_df and report_df to compute all metrics and breakdowns.
    """
    ASSET_CLASSES = ['ESOPs/RSU', 'Equity', 'Global Equity', 'Gold', 'Liquid', 'Real Estate', 'Retirement', 'Silver', 'Vehicle']
    
    cleaned_ac_rows = []
    
    if report_df is not None and not report_df.empty:
        col_names = report_df.columns.tolist()
        asset_class_col = col_names[0]
        category_col = col_names[1]
        invested_col = col_names[2]
        market_value_col = col_names[3]
        pct_col = col_names[4] if len(col_names) > 4 else None
        gain_loss_col = col_names[5] if len(col_names) > 5 else None
        gain_loss_pct_col = col_names[6] if len(col_names) > 6 else None
        
        current_class = None
        for idx, row in report_df.iterrows():
            val0 = row[asset_class_col]
            val1 = row[category_col] if category_col in row else None
            
            if pd.isnull(val0) and (pd.isnull(val1) if val1 is not None else True) and pd.isnull(row[market_value_col]):
                continue
                
            val0_str = str(val0).strip() if pd.notnull(val0) else ""
            if val0_str in ("Row Labels", "Values", "Grand Total", ""):
                continue
                
            if pd.notnull(val0) and val0_str:
                current_class = val0_str
                
            # We want Level 0 row (Category is null / empty) and only standard asset classes
            if current_class in ASSET_CLASSES and (pd.isnull(val1) if val1 is not None else True):
                inv = clean_num_val(row[invested_col])
                mv = clean_num_val(row[market_value_col])
                gl = clean_num_val(row[gain_loss_col]) if gain_loss_col else (mv - inv)
                
                # Gain/Loss %
                if gain_loss_pct_col:
                    gl_pct = clean_num_val(row[gain_loss_pct_col])
                    # If represented as fraction (e.g. 0.25 for 25%), convert to percent
                    if abs(gl_pct) <= 1.0 and gl_pct != 0:
                        gl_pct = gl_pct * 100
                else:
                    gl_pct = (gl / inv * 100) if inv > 0 else 0.0
                    
                cleaned_ac_rows.append({
                    "Asset Class": current_class,
                    "Invested": inv,
                    "Market Value": mv,
                    "Gain/Loss": gl,
                    "Gain/Loss %": gl_pct
                })
                
    ac_df = pd.DataFrame(cleaned_ac_rows)
    if not ac_df.empty:
        # Keep the first occurrence to avoid duplicates (e.g. Real Estate, Vehicle)
        ac_df = ac_df.drop_duplicates(subset=["Asset Class"])
    else:
        ac_df = pd.DataFrame(columns=["Asset Class", "Invested", "Market Value", "Gain/Loss", "Gain/Loss %"])
        
    # Calculate allocations
    total_market_value = ac_df["Market Value"].sum()
    total_invested = ac_df["Invested"].sum()
    total_gain = ac_df["Gain/Loss"].sum()
    total_gain_pct = (total_gain / total_invested * 100) if total_invested > 0 else 0.0
    
    if total_market_value > 0:
        ac_df["Allocation (%)"] = ac_df["Market Value"] / total_market_value * 100
    else:
        ac_df["Allocation (%)"] = 0.0
        
    asset_class_mv_map = dict(zip(ac_df["Asset Class"], ac_df["Market Value"]))
    
    # 2. Clean detailed holdings_df
    if holdings_df is not None and not holdings_df.empty:
        # Clean numeric fields in detailed sheet
        for col in ["Invested Amount", "Market Value", "Total Gain/Loss (INR)", "Total Gain/Loss (%)", "Holding (%)"]:
            if col in holdings_df.columns:
                holdings_df[col] = holdings_df[col].apply(clean_num_val)
                
        # Fill missing values
        if "First Name" in holdings_df.columns:
            holdings_df["First Name"] = holdings_df["First Name"].fillna("Unknown")
        else:
            holdings_df["First Name"] = "Unknown"
            
        # Group by Category (Cap-size)
        if "Category" in holdings_df.columns:
            cat_grp = holdings_df.groupby("Category")["Market Value"].sum().reset_index()
            cat_grp = cat_grp.sort_values(by="Market Value", ascending=False)
            cat_grp["Allocation (%)"] = cat_grp["Market Value"] / cat_grp["Market Value"].sum() * 100
        else:
            cat_grp = pd.DataFrame(columns=["Category", "Market Value", "Allocation (%)"])
            
        # Group by Broker
        if "Broker" in holdings_df.columns:
            broker_grp = holdings_df.groupby("Broker")["Market Value"].sum().reset_index()
            broker_grp = broker_grp.sort_values(by="Market Value", ascending=False)
            broker_grp["Allocation (%)"] = broker_grp["Market Value"] / broker_grp["Market Value"].sum() * 100
        else:
            broker_grp = pd.DataFrame(columns=["Broker", "Market Value", "Allocation (%)"])
            
        # Group by Family Member
        member_grp = holdings_df.groupby("First Name")["Market Value"].sum().reset_index()
        member_grp = member_grp.sort_values(by="Market Value", ascending=False)
        member_grp["Allocation (%)"] = member_grp["Market Value"] / member_grp["Market Value"].sum() * 100
        
        # Get Top 10 holdings
        top_holdings = holdings_df.sort_values(by="Market Value", ascending=False).head(10).copy()
        
    else:
        cat_grp = pd.DataFrame(columns=["Category", "Market Value", "Allocation (%)"])
        broker_grp = pd.DataFrame(columns=["Broker", "Market Value", "Allocation (%)"])
        member_grp = pd.DataFrame(columns=["First Name", "Market Value", "Allocation (%)"])
        top_holdings = pd.DataFrame()
        
    return {
        "total_market_value": total_market_value,
        "total_invested": total_invested,
        "total_gain": total_gain,
        "total_gain_pct": total_gain_pct,
        "asset_class_df": ac_df,
        "asset_class_mv_map": asset_class_mv_map,
        "category_df": cat_grp,
        "broker_df": broker_grp,
        "member_df": member_grp,
        "top_holdings_df": top_holdings,
        "clean_holdings_df": holdings_df
    }
