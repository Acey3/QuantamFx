"""Database storage for the Forex bot."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = "forex_bot.db"

def init_db():
    """Initialize the SQLite database with required tables."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Table for general bot scans/runs
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            status TEXT
        )
    """)
    
    # Table for all signals/indicators processed (even if not sent to Telegram)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            symbol TEXT,
            bar_time TEXT,
            price REAL,
            rsi REAL,
            ema50 REAL,
            ema200 REAL,
            macd_line REAL,
            macd_signal REAL,
            signal_type TEXT,  -- BUY, SELL, NO SIGNAL
            is_actionable INTEGER -- 1 if BUY/SELL, 0 otherwise
        )
    """)
    
    # Table for alerts/messages actually sent to Telegram
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            message TEXT,
            dedup_key TEXT
        )
    """)
    
    # Table for historical trades (to be used by backtester or manual entry)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            symbol TEXT,
            side TEXT,
            entry_price REAL,
            exit_price REAL,
            pnl_cash REAL,
            outcome TEXT
        )
    """)
    
    conn.commit()
    conn.close()

def log_scan(status: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO scans (status) VALUES (?)", (status,))
    conn.commit()
    conn.close()

def log_signal(symbol, bar_time, price, rsi, ema50, ema200, macd_line, macd_signal, signal_type, is_actionable):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO signals (symbol, bar_time, price, rsi, ema50, ema200, macd_line, macd_signal, signal_type, is_actionable)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (symbol, bar_time, price, rsi, ema50, ema200, macd_line, macd_signal, signal_type, 1 if is_actionable else 0))
    conn.commit()
    conn.close()

def log_alert(message, dedup_key):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO alerts (message, dedup_key) VALUES (?, ?)", (message, dedup_key))
    conn.commit()
    conn.close()

def log_trade(symbol, side, entry_price, exit_price, pnl_cash, outcome):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO trades (symbol, side, entry_price, exit_price, pnl_cash, outcome)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (symbol, side, entry_price, exit_price, pnl_cash, outcome))
    conn.commit()
    conn.close()
