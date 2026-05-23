import sys
from invest_ai.tools.technical import get_price_history

try:
    print(get_price_history("AAPL", "1mo"))
except Exception as e:
    print("Error:", e)
