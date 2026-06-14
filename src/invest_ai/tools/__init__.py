from .stock_data import (
    get_stock_price, get_company_info, get_analyst_recommendations,
    get_historical_data, compare_stocks,
)
from .technical import (
    get_moving_averages, get_rsi, get_macd,
    get_bollinger_bands, get_full_technical_analysis,
)
from .fundamentals import (
    get_valuation_metrics, get_income_statement,
    get_balance_sheet, get_cash_flow, get_dividends,
)
from .news import search_stock_news, get_market_news
from .live_intel import (
    get_earnings_history,
    get_analyst_estimates,
    get_upcoming_catalysts,
    get_insider_activity,
    get_institutional_changes,
    search_company_operations,
)

ALL_TOOLS = [
    get_stock_price, get_company_info, get_analyst_recommendations,
    get_historical_data, compare_stocks,
    get_moving_averages, get_rsi, get_macd,
    get_bollinger_bands, get_full_technical_analysis,
    get_valuation_metrics, get_income_statement,
    get_balance_sheet, get_cash_flow, get_dividends,
    search_stock_news, get_market_news,
]

TECHNICAL_TOOLS = [
    get_moving_averages, get_rsi, get_macd,
    get_bollinger_bands, get_full_technical_analysis,
    get_stock_price, get_historical_data,
]

FUNDAMENTAL_TOOLS = [
    get_valuation_metrics, get_income_statement,
    get_balance_sheet, get_cash_flow, get_dividends,
    get_company_info, get_analyst_recommendations,
]

NEWS_TOOLS = [search_stock_news, get_market_news]

LIVE_INTEL_TOOLS = [
    get_earnings_history,
    get_analyst_estimates,
    get_upcoming_catalysts,
    get_insider_activity,
    get_institutional_changes,
    search_company_operations,
]

__all__ = [
    "ALL_TOOLS", "TECHNICAL_TOOLS", "FUNDAMENTAL_TOOLS", "NEWS_TOOLS",
    "LIVE_INTEL_TOOLS",
]
