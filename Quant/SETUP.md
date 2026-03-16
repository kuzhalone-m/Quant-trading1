# BEEW QUANTUM — Setup & Run Guide

## ⚡ Get Running Today (Step by Step)

---

### STEP 1 — Install Python (if not already)
1. Go to [python.org/downloads](https://python.org/downloads)
2. Download **Python 3.11** for Windows
3. ✅ During install: **tick "Add Python to PATH"**
4. Click Install

Verify:
```
python --version
```
Should show: `Python 3.11.x`

---

### STEP 2 — Open MetaTrader 5 & Enable Algo Trading
1. Open MetaTrader 5 on your PC (download from broker if needed)
2. Log in to your **DEMO account**
3. Go to: **Tools → Options → Expert Advisors**
4. ✅ Tick: **"Allow algorithmic trading"**
5. ✅ Tick: **"Allow DLL imports"**
6. Click OK
7. Verify: you see a green "Algo Trading" button in the toolbar

---

### STEP 3 — Install Required Libraries
Open a Windows Terminal / PowerShell in the Quant folder:

```powershell
cd "C:\Users\marke\OneDrive\Documents\Beew\Antigravity\Quant"
pip install -r requirements.txt
```

---

### STEP 4 — Configure Your Account
Open `config.py` in any text editor (or VS Code) and fill in:

```python
MT5_LOGIN    = 123456789      # your MT5 demo account number
MT5_PASSWORD = "YourPassword" # your demo account password
MT5_SERVER   = "Pepperstone-Demo"  # your broker's server name
```

> 💡 Find the server name in MT5: File → Open Account → look at server list

---

### STEP 5 — Test Everything First
```powershell
python test_connection.py
```

You should see:
```
✅ Connected!
✅ Got 150 candles on M15
✅ Lot size calculated
✅ ALL CHECKS PASSED
```

If you get errors, see Troubleshooting below.

---

### STEP 6 — Run the Bot!
```powershell
python main.py
```

The bot will:
-  Connect to MT5
-  Wait for each 15-minute candle to close
-  Run the EMA+RSI+ATR strategy
-  If signal confidence ≥ 60%, place a trade
-  Log everything to `logs/trades.csv`
-  Print status updates every candle

To stop the bot: Press **Ctrl+C**

---

### STEP 7 — Review Trades
After running, open `logs/trades.csv` in Excel to see:
- All trades placed (entry, SL, TP, lots, confidence)
- Whether they hit TP or SL
- P&L per trade

---

## 🛡 Risk Rules (Built In — Cannot Be Bypassed)

| Rule | Value |
|------|-------|
| Risk per trade | 0.5% of equity |
| Max daily loss | 4% of equity |
| Max overall loss | 10% of initial balance |
| Max concurrent trades | 3 |
| Min hold time | 2 minutes (no HFT) |

---

## 🔍 Strategy Logic (EMA Cross + RSI + ATR)

**BUY when ALL of these are true:**
- EMA 9 crosses above EMA 21 (upward momentum)
- Price is above EMA 50 on H1 (higher timeframe bullish)
- RSI < 65 (not overbought)
- ATR above 20-candle average (volatility present)

**SELL when ALL of these are true:**
- EMA 9 crosses below EMA 21 (downward momentum)
- Price below EMA 50 on H1 (higher timeframe bearish)
- RSI > 35 (not oversold)
- ATR above average

**SL** = Entry ± (ATR × 1.5)  
**TP** = Entry ± (ATR × 2.5)  → ~1:1.67 Risk:Reward

---

## 🔧 Troubleshooting

**"Cannot connect to MT5"**
→ Make sure MT5 is open and you're logged in
→ Enable Algo Trading in Tools → Options → Expert Advisors

**"No candle data for XAUUSD"**
→ Open XAUUSD in MT5 chart once, then retry (this loads it)
→ Some brokers use GOLD instead of XAUUSD — update config.py

**"Order failed: retcode=10004"**
→ Market is closed (weekends). Test during market hours (Mon–Fri)

**"ModuleNotFoundError: MetaTrader5"**
→ Run: `pip install MetaTrader5`
→ Note: MetaTrader5 Python library only works on Windows

---

## 📁 File Structure

```
Quant/
├── main.py             ← 🚀 Run this to start the bot
├── test_connection.py  ← ✅ Run this first to verify setup
├── config.py           ← ⚙️ All settings here
├── mt5_client.py       ← MT5 data & connection
├── strategy.py         ← Signal engine (STRATUS)
├── risk_engine.py      ← Risk management (KAVACH)
├── executor.py         ← Order placement (ZEPHYR)
├── trade_logger.py     ← CSV trade logging
├── alert.py            ← Telegram notifications
├── requirements.txt    ← Python packages needed
└── logs/
    ├── trading_bot.log ← Full bot logs
    └── trades.csv      ← Trade history
```
