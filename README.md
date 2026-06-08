# 📊 TradingView Alert System

A real-time trading alert system that delivers **4H candle close notifications** and **high-impact economic news warnings** directly to your phone via Telegram — fully deployed in the cloud with no laptop required.

![Python](https://img.shields.io/badge/Python-3.14-blue?style=flat-square&logo=python)
![Flask](https://img.shields.io/badge/Flask-3.0-black?style=flat-square&logo=flask)
![Railway](https://img.shields.io/badge/Deployed-Railway-purple?style=flat-square)
![Telegram](https://img.shields.io/badge/Notifications-Telegram-blue?style=flat-square&logo=telegram)

---

## 🚀 Features

- **4H Candle Close Alerts** — Instant Telegram notification whenever a 4-hour candle closes on any watched pair
- **Economic Calendar Monitoring** — Scans for high-impact news events every 5 minutes and warns you 30 minutes in advance
- **Daily Morning Briefing** — Sends a 7am summary of all major economic events for the day
- **Forecast & Previous Data** — Each news alert includes the forecast and previous values for the economic release
- **Fully Cloud-Hosted** — Runs 24/7 on Railway with no local machine required
- **Secure Webhooks** — Password-protected endpoint prevents unauthorised triggers

---

## 🎯 Instruments Monitored

| Instrument | Currencies Watched | Key Events |
|------------|-------------------|------------|
| GBPUSD | GBP, USD | BOE decisions, UK CPI, US NFP, FOMC |
| GBPJPY | GBP, JPY | BOE decisions, BOJ decisions, UK/Japan CPI |
| US Oil (WTI) | USD | EIA inventory, OPEC, US NFP |
| NAS100 | USD | FOMC, US CPI, NFP, Tech earnings |
| German 40 (DAX) | EUR | ECB decisions, German CPI/GDP |

---

## 🏗️ Architecture

```
TradingView (chart alert)
        │
        │  Webhook (HTTP POST)
        ▼
┌─────────────────────┐        ┌──────────────────────────┐
│    server.py        │        │    calendar_poller.py    │
│   (Railway Web)     │        │   (Railway Worker)       │
│                     │        │                          │
│  Receives webhook   │        │  Polls ForexFactory      │
│  from TradingView   │        │  calendar every 5 mins   │
│  on candle close    │        │  for high-impact events  │
└────────┬────────────┘        └────────────┬─────────────┘
         │                                  │
         │         Telegram Bot API         │
         └──────────────┬───────────────────┘
                        ▼
                 📱 Your Phone
```

---

## 🛠️ Tech Stack

- **Backend:** Python, Flask
- **Notifications:** Telegram Bot API
- **Economic Data:** ForexFactory Calendar Feed
- **Deployment:** Railway (Web Service + Background Worker)
- **Source Control:** GitHub

---

## ⚙️ Setup & Deployment

### Prerequisites
- Python 3.11+
- Telegram Bot Token (via [@BotFather](https://t.me/botfather))
- TradingView account
- Railway account

### 1. Clone the repository
```bash
git clone https://github.com/YOUR_USERNAME/tradingview-alerts.git
cd tradingview-alerts
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure your credentials
Open `server.py` and `calendar_poller.py` and update:
```python
TELEGRAM_TOKEN   = "your_telegram_bot_token"
TELEGRAM_CHAT_ID = "your_chat_id"
WEBHOOK_SECRET   = "your_chosen_password"
```

### 4. Deploy to Railway
1. Push repo to GitHub
2. Go to [railway.app](https://railway.app) → New Project → GitHub Repo
3. Railway auto-detects the `Procfile` and deploys both services:
   - **Web service** → `server.py` (receives TradingView webhooks)
   - **Worker** → `calendar_poller.py` (monitors economic calendar)

### 5. Set up TradingView alerts
For each instrument, create an alert in TradingView with:
- **Condition:** Once Per Bar Close
- **Webhook URL:** `https://your-railway-url.up.railway.app/webhook?secret=YOUR_PASSWORD`
- **Message:**
```json
{
  "type": "candle_close",
  "pair": "GBPUSD",
  "timeframe": "4H",
  "message": "4H candle closed on GBPUSD at {{close}}. H:{{high}} L:{{low}}"
}
```

---

## 📱 Notification Examples

**4H Candle Close:**
```
🕯️ 4H Candle Closed — GBPUSD

4H candle closed on GBPUSD at 1.27045. H:1.27123 L:1.26891
```

**High Impact News Warning:**
```
🚨 HIGH IMPACT NEWS in 28 mins
━━━━━━━━━━━━━━━━━━━━
📌 Non-Farm Employment Change
📖 new jobs added in the US (excl. farming)

💱 Currency: USD
🕐 Time: 13:30 (Accra UTC+0)
📊 Affects: GBPUSD, US Oil, NAS100

━━━━━━━━━━━━━━━━━━━━
📈 Forecast: 185K
📉 Previous: 177K
━━━━━━━━━━━━━━━━━━━━
⚠️ Consider managing open positions on GBPUSD, US Oil, NAS100
```

---

## 📁 Project Structure

```
tradingview-alerts/
├── server.py              # Flask webhook server (deployed to Railway web)
├── calendar_poller.py     # Economic calendar monitor (Railway worker)
├── requirements.txt       # Python dependencies
├── Procfile               # Railway process definitions
└── README.md              # This file
```

---

## 🔒 Security

- Webhook endpoint is protected by a secret key passed as a URL parameter
- Unauthorised requests are rejected with a 401 response
- Telegram credentials stored directly in config (recommend moving to environment variables for production)

---

## 🗺️ Roadmap

- [ ] Add NewsAPI integration for geopolitical headline alerts
- [ ] Add actual vs forecast comparison on news release
- [ ] Web dashboard to view alert history
- [ ] Support for more instruments and currencies
- [ ] Move credentials to environment variables

---

## 👨‍💻 Author

**Ben** — Software Engineering Student | Accra, Ghana
Interests: AI/ML Engineering, Algorithmic Trading, Cloud Deployment

---

## 📄 Licence

MIT Licence — feel free to fork and adapt for your own trading setup.
