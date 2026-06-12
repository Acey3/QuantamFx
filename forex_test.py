"""Backward-compatible runner for the modular Forex bot.

The implementation was split into:
- config.py
- data.py
- indicators.py
- telegram_bot.py
- main.py

This file simply calls main.run_bot().
"""

from main import run_bot


if __name__ == "__main__":
    run_bot()

