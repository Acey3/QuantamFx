- [x] Inspect forex_test.py for the error source
- [x] Split forex_test.py into modules: config.py, data.py, indicators.py, telegram_bot.py, main.py
- [x] Make forex_test.py a backward-compatible runner that calls main.run_bot()
- [x] Run a quick compile check + execute forex_test.py to confirm Telegram message works

- [x] Add logging
- [x] Add exception handling around Telegram send
- [x] Add current market price (Close)
- [x] Add timestamp (UTC)
- [x] Prevent duplicate alerts (stores last signal in bot_state.json)
- [x] Save last signal to file

- [x] Add additional symbols (multi-symbol alerts)
- [x] Replace unsupported XAUUSD=X with GC=F (Yahoo gold futures)

