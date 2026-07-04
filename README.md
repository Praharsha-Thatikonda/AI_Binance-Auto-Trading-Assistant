# 📈 AI Binance Auto Trading Assistant

Welcome to the **AI Binance Auto Trading Assistant**! This is an automated trading application built with FastAPI and Web3 integration that provides an intuitive dashboard for managing your cryptocurrency trades, alongside powerful AI-driven market analysis.

---

## ✨ Features 

- **🔐 Binance Integration**: Securely connect to your Binance account using API Keys.
- **💰 Real-time Balance**: View your current wallet balances directly from the unified dashboard.
- **🤖 AI Market Analysis**: Leverage advanced AI algorithms to get market insights and real-time trading signals (Buy/Sell/Hold).
- **🎨 Modern UI**: Enjoy a sleek, dark-themed, and responsive web interface designed for a seamless user experience.
- **📊 Real-time Data**: Get up-to-date market statistics and trading pairs (e.g., BTC/USDT).

---

## 📸 Application Screenshots

Here is a look at the application's interface and capabilities:

### Dashboard & Analytics
<div align="center">
  <img src="Pics/Screenshot%202026-07-03%20153915.png" alt="Dashboard View 1" width="400"/>
  <img src="Pics/Screenshot%202026-07-03%20153956.png" alt="Dashboard View 2" width="400"/>
</div>

### AI Insights & Trading Signals
<div align="center">
  <img src="Pics/Screenshot%202026-07-03%20154508.png" alt="AI Insights 1" width="400"/>
  <img src="Pics/Screenshot%202026-07-03%20160151.png" alt="AI Insights 2" width="400"/>
</div>

### Wallet & Account Management
<div align="center">
  <img src="Pics/Screenshot%202026-07-03%20160218.png" alt="Wallet View" width="400"/>
  <img src="Pics/Screenshot%202026-07-03%20161333.png" alt="Account Management 1" width="400"/>
</div>

### Settings & Controls
<div align="center">
  <img src="Pics/Screenshot%202026-07-03%20161822.png" alt="Settings View" width="400"/>
  <img src="Pics/Screenshot%202026-07-03%20161904.png" alt="Controls View" width="400"/>
  <img src="Pics/Screenshot%202026-07-03%20162120.png" alt="Final View" width="400"/>
</div>

---

## 🚀 Setup & Installation

Follow these steps to run the application locally:

### 1. Install Dependencies
Ensure you have Python installed, then install the required packages:
```bash
pip install -r requirements.txt
```

### 2. Initialize the Database
Run the setup scripts to ensure the SQLite databases are correctly configured:
```bash
python fix_db_tables.py
python check_web3_db.py
```

### 3. Run the Application
Start the FastAPI server:
```bash
uvicorn app.main:app --reload
```

### 4. Access the Dashboard
Open your web browser and navigate to:
```
http://127.0.0.1:8000
```

---

## 🛠️ Usage

1. **Connect Binance**: Navigate to the login/settings page and enter your Binance API Key and Secret Key. 
   *(Note: Keys are managed securely and are only used to authenticate your session).*
2. **Monitor Dashboard**: Once authenticated, the dashboard will populate with your real-time wallet balance and market trends.
3. **AI Auto-Trader**: Use the built-in AI tools to analyze specific trading pairs like `BTC/USDT` and review the generated Buy/Sell/Hold signals.
4. **Execute Trades**: Use the signals to make informed trading decisions.

---

## ⚠️ Disclaimer

**Risk Warning**: Cryptocurrency trading involves significant risk and can result in the loss of your capital. This application is provided for educational and assistance purposes only. The AI analysis should be treated as a simulation and tool, and **should not be taken as financial advice**. Always do your own research before trading.
