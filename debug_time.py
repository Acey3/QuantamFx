import yfinance as yf
from datetime import datetime

symbol = "GC=F"
ticker = yf.Ticker(symbol)

print(f"Current System Time: {datetime.now()}")
print(f"Market Status: {ticker.info.get('marketState')}")

history = ticker.history(period="1d", interval="15m")
if not history.empty:
    print(f"Latest Bar Timestamp: {history.index[-1]}")
    print(f"Latest Bar Price: {history.iloc[-1]['Close']}")
else:
    print("No history returned for period='1d'")

# Check if maybe '5d' returns something newer
history_5d = ticker.history(period="5d", interval="15m")
if not history_5d.empty:
    print(f"Latest Bar in 5d history: {history_5d.index[-1]}")
else:
    print("No history returned for period='5d'")
