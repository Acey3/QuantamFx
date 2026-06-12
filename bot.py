import pandas as pd
import requests
import yfinance as yf
from ta.momentum import RSIIndicator

print("Starting bot")
TOKEN = "8999178474:AAEaAePLHnt2iAeocrbwmZ_5Ek0JPLfVaSk"
CHAT_ID = "6844390130"

data = yf.download("EURUSD=X", period="5d", interval="15m")

close = data["Close"].squeeze()

rsi = RSIIndicator(close, window=14).rsi()
current_rsi = rsi.iloc[-1]

if current_rsi<30:
    message = f"🚀 BUY SIGNAL\n\nEUR/USD\nRSI:{current_rsi:.2f}"
elif current_rsi>70:
    message = f"🔻 SELL SIGNAL\n\nEUR/USD\nRSI:{current_rsi:.2f}"
else:
    message = f"⚠️ NO SIGNAL\n\nEUR/USD\nRSI:{current_rsi:.2f}"


url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
requests.post(url, data={
    "chat_id": CHAT_ID,
    "text": message
})

print(message)