# 📊 Trading News Alert System

A fully automated, cloud-hosted trading intelligence system that delivers **4H candle close notifications**, **high-impact economic news warnings**, **actual data releases with reaction signals**, and **bi-hourly market intelligence reports** — all sent directly to your phone via Telegram with no laptop required.

![Python](https://img.shields.io/badge/Python-3.14-blue?style=flat-square&logo=python)
![Flask](https://img.shields.io/badge/Flask-3.0-black?style=flat-square&logo=flask)
![Railway](https://img.shields.io/badge/Deployed-Railway-purple?style=flat-square)
![Telegram](https://img.shields.io/badge/Notifications-Telegram-blue?style=flat-square&logo=telegram)
![BeautifulSoup](https://img.shields.io/badge/Scraping-BeautifulSoup4-green?style=flat-square)

---

## 🚀 Features

- **4H Candle Close Alerts** — Instant Telegram notification whenever a 4-hour candle closes on any watched pair
- **Pre-Event Warning** — Warns you 30 minutes before any high-impact economic event with forecast and previous values
- **Actual Data Release** — Sends the actual figure the moment it drops, alongside forecast and previous for comparison
- **Reaction Signal** — Automatically calculates whether the release beats or misses forecast and signals the directional bias
- **Market Intelligence Scan** — Scrapes 5 financial news sources every 2 hours and scores each headline for sentiment and impact probability per pair
- **Daily Morning Briefing** — Sends a 7am summary of all high-impact events for the day
- **Fully Cloud-Hosted** — All 3 services run 24/7 on Railway with no local machine required
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
┌─────────────────────┐
│    server.py        │  ← Railway Web Service
│                     │
│  Receives webhook   │
│  on 4H candle close │
└────────┬────────────┘
         │
         │  Telegram Bot API
         ▼
      📱 Your Phone
         ▲
         │  Telegram Bot API
         │
┌────────┴────────────┐       ┌──────────────────────────┐
│  calendar_poller.py │       │     news_scraper.py      │
│  Railway Worker     │       │     Railway Worker       │
│                     │       │                          │
│  • 30min pre-warning│       │  Scrapes every 2 hours:  │
│  • Actual releases  │       │  • ForexLive             │
│  • Beats/misses     │       │  • FXStreet              │
│    forecast signal  │       │  • Investing.com         │
│  • Daily 7am brief  │       │  • OilPrice              │
│                     │       │  • Reuters               │
└─────────────────────┘       │                          │
                              │  Scores each headline:   │
                              │  • Sentiment analysis    │
                              │  • Impact probability    │
                              │    per pair              │
                              └──────────────────────────┘
```

---

## 📱 Notification Examples

**30-Minute Pre-Event Warning:**
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
⚠️ Consider managing open positions
```

**Actual Data Release:**
```
📊 ACTUAL DATA RELEASED
━━━━━━━━━━━━━━━━━━━━
📌 Non-Farm Employment Change

💱 Currency: USD
🕐 Released: 13:30 (Accra UTC+0)
📊 Affects: GBPUSD, US Oil, NAS100

━━━━━━━━━━━━━━━━━━━━
🎯 Actual:   227K
📈 Forecast: 185K
📉 Previous: 177K
━━━━━━━━━━━━━━━━━━━━
⚡ Reaction Signal: BEATS FORECAST by 42.00 → Bullish USD
👁 Watch GBPUSD, US Oil, NAS100 for immediate price reaction
```

**Market Intelligence Report:**
```
🌐 Market Intelligence Report
🕐 14:00 UTC | 3 relevant headlines
━━━━━━━━━━━━━━━━━━━━

1. Bank of England signals prolonged rate hold
📌 ForexLive
📈 Sentiment: BEARISH (78% confidence)
   🔴 GBPUSD: 82% impact probability
   🔴 GBPJPY: 79% impact probability
━━━━━━━━━━━━━━━━━━━━

🔴 High (75%+)  🟡 Medium (55–74%)  🟢 Lower (40–54%)
```

**4H Candle Close:**
```
🕯️ 4H Candle Closed — GBPUSD

4H candle closed on GBPUSD at 1.27045. H:1.27123 L:1.26891
```

---

## 🛠️ Tech Stack

- **Backend:** Python, Flask
- **Notifications:** Telegram Bot API
- **Economic Data:** ForexFactory Calendar Feed
- **Web Scraping:** BeautifulSoup4 (ForexLive, FXStreet, Investing.com, OilPrice, Reuters)
- **Sentiment Analysis:** Keyword-based scorer (FinBERT upgrade path included in code)
- **Deployment:** Railway (1 Web Service + 2 Background Workers)
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
git clone https://github.com/ben244294/tradingview-alerts.git
cd tradingview-alerts
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure credentials
Update these values in `server.py`, `calendar_poller.py` and `news_scraper.py`:
```python
TELEGRAM_TOKEN   = "your_telegram_bot_token"
TELEGRAM_CHAT_ID = "your_chat_id"
WEBHOOK_SECRET   = "your_chosen_password"   # server.py only
```

### 4. Deploy to Railway
Push repo to GitHub then on [railway.app](https://railway.app):

| Service | Type | Start Command |
|---------|------|--------------|
| Webhook receiver | Web Service | `python server.py` |
| Calendar & actuals | Background Worker | `python calendar_poller.py` |
| News scraper | Background Worker | `python news_scraper.py` |

Railway auto-installs from `requirements.txt` on every deploy.

### 5. Set up TradingView alerts
For each instrument create an alert with:
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
Repeat for: GBPJPY, USOIL, NAS100, GER40

---

## 📁 Project Structure

```
tradingview-alerts/
├── server.py              # Flask webhook server (Railway web service)
├── calendar_poller.py     # Economic calendar + actual data releases (Railway worker)
├── news_scraper.py        # Bi-hourly market intelligence scraper (Railway worker)
├── requirements.txt       # Python dependencies
├── Procfile               # Railway process definitions
└── README.md              # This file
```

---

## ⏰ Automated Schedule

| Notification | Trigger |
|-------------|---------|
| 📅 Daily economic preview | Every day at 7:00 AM |
| 🚨 Pre-event warning | 30 minutes before high-impact news |
| 📊 Actual data release | Minutes after data drops |
| ⚡ Beats/misses signal | With every actual release |
| 🌐 Market intelligence scan | Every 2 hours, 5 sources |
| 🕯️ 4H candle close | Every 4H bar close via TradingView |

---

## 🔒 Security

- Webhook endpoint protected by secret key in URL parameter
- Unauthorised requests rejected with 401 response
- Recommend moving credentials to Railway environment variables for production

---

## 🗺️ Roadmap

- [ ] Upgrade sentiment scoring from keyword-based to FinBERT transformer model
- [ ] Add NewsAPI integration for broader geopolitical headline coverage
- [ ] Add actual vs forecast deviation percentage to reaction signal
- [ ] Web dashboard to view alert history and sentiment trends
- [ ] Autonomous trade execution via OANDA API
- [ ] React frontend with live pair sentiment display
- [ ] Move credentials to environment variables

---

## 👨‍💻 Author

**Ben  — Software Engineering Student | Accra, Ghana
Interests: AI/ML Engineering, Algorithmic Trading, Cloud Deployment

---

## 📄 Licence

MIT Licence — feel free to fork and adapt for your own trading setup.
