"""
Market Intelligence Scraper
============================
Scrapes financial news from multiple sources at optimal market times,
scores headlines with sentiment analysis, filters accurately per pair,
calculates impact probability and duration, then sends to Telegram.

Keep-alive ping every 10 mins to prevent Render free tier sleep.

Pairs: GBPUSD, GBPJPY, XAUUSD, XAGUSD, BTCUSD, ETHUSD,
       US Oil, NAS100, German 40

Optimal scan times (UTC):
  06:00 — Pre-London open
  08:00 — London open (highest FX volatility)
  12:00 — London/NY overlap (highest volume)
  15:00 — NY afternoon (US data window)
  19:00 — NY close / crypto evening
  22:00 — Asian open + crypto overnight
"""

import requests
import schedule
import time
import logging
import re
from datetime import datetime, timezone
from bs4 import BeautifulSoup

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────
TELEGRAM_TOKEN    = "8282705170:AAHM0iAJ50WESe79IZMUyxXAg5aUc9q7Gno"
TELEGRAM_CHAT_ID  = "7936995648"
TELEGRAM_URL      = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

# Your Render web service URL — keeps server.py awake
RENDER_URL        = "https://tradingview-alerts-gbov.onrender.com"

MIN_IMPACT_THRESHOLD     = 50
MAX_HEADLINES_PER_REPORT = 6
MIN_HEADLINE_LENGTH      = 30
# ─────────────────────────────────────────────

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# ─────────────────────────────────────────────
# PAIR KEYWORDS — primary, secondary, exclude
# ─────────────────────────────────────────────
PAIR_CONFIG = {
    "GBPUSD": {
        "primary": [
            "bank of england", "boe rate", "uk inflation", "uk cpi",
            "uk gdp", "pound sterling", "gbp", "uk interest rate",
            "uk unemployment", "uk jobs", "federal reserve", "fomc rate",
            "us interest rate", "us nonfarm", "non-farm payroll"
        ],
        "secondary": [
            "sterling", "pound", "dollar index", "usd", "us economy",
            "us gdp", "us cpi", "us inflation", "powell", "bailey"
        ],
        "exclude": ["australian", "canadian", "nzd", "aud", "cad"]
    },
    "GBPJPY": {
        "primary": [
            "bank of england", "boe rate", "bank of japan", "boj rate",
            "pound yen", "gbpjpy", "uk inflation", "japan inflation",
            "uk interest rate", "japan interest rate"
        ],
        "secondary": [
            "sterling", "pound", "yen", "jpy", "japanese economy",
            "japan cpi", "tokyo cpi", "ueda", "bailey"
        ],
        "exclude": ["australian", "canadian", "nzd", "aud", "cad"]
    },
    "XAUUSD": {
        "primary": [
            "gold price", "gold rally", "gold falls", "gold rises",
            "gold demand", "central bank gold", "gold reserves",
            "safe haven demand", "federal reserve rate", "real yields",
            "us treasury yields", "geopolitical risk", "gold etf"
        ],
        "secondary": [
            "gold", "xau", "bullion", "precious metal", "safe haven",
            "risk off", "inflation hedge", "dollar weakness", "fed rate",
            "war", "conflict", "crisis", "recession fears"
        ],
        "exclude": ["gold miner stock", "gold mining company"]
    },
    "XAGUSD": {
        "primary": [
            "silver price", "silver demand", "silver supply",
            "silver rally", "silver falls", "industrial silver",
            "solar panel demand", "silver etf"
        ],
        "secondary": [
            "silver", "xag", "precious metals", "industrial demand",
            "manufacturing pmi", "commodities", "gold silver ratio",
            "safe haven", "inflation hedge"
        ],
        "exclude": ["silver screen", "silver anniversary", "sterling silver jewel"]
    },
    "BTCUSD": {
        "primary": [
            "bitcoin price", "bitcoin rally", "bitcoin falls",
            "bitcoin etf", "btc price", "crypto regulation",
            "sec bitcoin", "bitcoin halving", "bitcoin adoption",
            "institutional bitcoin", "blackrock bitcoin", "spot bitcoin etf"
        ],
        "secondary": [
            "bitcoin", "btc", "cryptocurrency", "crypto market",
            "digital asset", "blockchain", "crypto regulation",
            "risk appetite", "fed rate crypto", "binance", "coinbase"
        ],
        "exclude": ["bitcoin scam", "bitcoin fraud", "crypto hack lost"]
    },
    "ETHUSD": {
        "primary": [
            "ethereum price", "ethereum rally", "ethereum falls",
            "eth price", "ethereum etf", "ethereum upgrade",
            "ethereum staking", "defi ethereum", "layer 2 ethereum",
            "spot ethereum etf", "sec ethereum"
        ],
        "secondary": [
            "ethereum", "eth", "ether", "crypto market", "altcoin",
            "defi", "smart contract", "layer 2", "blockchain",
            "digital asset", "cryptocurrency", "risk appetite"
        ],
        "exclude": ["ethereum scam", "ethereum hack", "eth stolen"]
    },
    "US Oil": {
        "primary": [
            "crude oil price", "wti crude", "brent crude",
            "opec production", "opec cut", "opec meeting",
            "eia crude inventory", "oil supply", "oil demand outlook",
            "us oil production", "iran oil sanction", "russia oil"
        ],
        "secondary": [
            "oil", "crude", "petroleum", "energy prices", "barrel",
            "gasoline", "natural gas", "saudi arabia", "opec+",
            "oil reserves", "energy crisis"
        ],
        "exclude": ["olive oil", "cooking oil", "palm oil"]
    },
    "NAS100": {
        "primary": [
            "nasdaq falls", "nasdaq rallies", "nasdaq futures",
            "tech stocks sell", "tech stocks rally", "us stocks",
            "federal reserve rate decision", "us cpi impact markets",
            "nvidia earnings", "apple earnings", "microsoft earnings",
            "google earnings", "amazon earnings", "meta earnings",
            "semiconductor outlook"
        ],
        "secondary": [
            "nasdaq", "tech stocks", "s&p 500", "wall street",
            "risk appetite", "us equity", "rate hike stocks",
            "fed pivot", "powell", "ai stocks", "semiconductor",
            "nvidia", "apple", "microsoft", "google", "amazon"
        ],
        "exclude": ["nasdaq listing", "ipo nasdaq", "nyse"]
    },
    "German 40": {
        "primary": [
            "dax falls", "dax rallies", "dax futures",
            "ecb rate decision", "ecb interest rate",
            "german gdp", "german cpi", "german inflation",
            "eurozone gdp", "eurozone cpi", "lagarde speech",
            "ifo business climate"
        ],
        "secondary": [
            "dax", "german 40", "european stocks", "ecb",
            "eurozone economy", "euro zone", "germany economy",
            "eu inflation", "european central bank", "lagarde",
            "euro", "eur"
        ],
        "exclude": ["nasdaq", "ftse", "dow jones"]
    },
}

# ─────────────────────────────────────────────
# DURATION RULES
# ─────────────────────────────────────────────
DURATION_RULES = [
    (["interest rate decision", "rate decision", "fomc statement",
      "boe rate", "boj rate", "ecb rate", "central bank"],
     "1–3 days", 48),
    (["geopolitical", "war", "conflict", "sanction", "crisis",
      "emergency meeting", "military"],
     "days to weeks", 120),
    (["opec cut", "opec production", "opec meeting", "iran sanction",
      "russia oil", "saudi arabia output"],
     "1–2 days", 36),
    (["bitcoin etf", "ethereum etf", "sec bitcoin", "sec ethereum",
      "crypto regulation", "bitcoin halving"],
     "1–3 days", 48),
    (["nonfarm", "non-farm payroll", "gdp", "unemployment rate"],
     "4–8 hours", 6),
    (["cpi", "inflation", "ppi", "core inflation"],
     "4–8 hours", 6),
    (["earnings", "quarterly profit", "revenue beat", "revenue miss"],
     "1–2 days", 36),
    (["pmi", "retail sales", "consumer confidence", "trade balance"],
     "2–4 hours", 3),
    (["powell", "lagarde", "bailey", "ueda", "speech", "testimony",
      "press conference", "statement"],
     "2–6 hours", 4),
    (["bitcoin price", "ethereum price", "crypto market",
      "btc", "eth rally", "crypto sell"],
     "1–4 hours", 2),
]

DEFAULT_DURATION = ("1–3 hours", 2)

NOISE_PHRASES = [
    "sponsored", "advertisement", "subscribe now", "click here",
    "sign up", "free trial", "webinar", "podcast episode",
    "weekly roundup", "morning briefing", "evening wrap",
    "this week in", "last week in", "monthly review",
    "how to trade", "quiz", "opinion:", "editorial:"
]

BULLISH_WORDS = [
    "rises", "surges", "jumps", "gains", "rallies", "beats",
    "exceeds", "stronger", "growth", "higher", "hawkish",
    "rate hike", "above expectations", "better than expected",
    "record high", "expansion", "robust", "safe haven demand",
    "institutional buying", "breakout", "all time high"
]

BEARISH_WORDS = [
    "falls", "drops", "plunges", "slides", "misses", "weaker",
    "slowdown", "lower", "dovish", "rate cut", "below expectations",
    "worse than expected", "record low", "contraction", "crisis",
    "risk off", "sell-off", "recession", "fears", "concern",
    "warning", "crash", "tumbles", "slumps"
]

HIGH_IMPACT_TRIGGERS = [
    "interest rate", "rate decision", "inflation", "cpi", "gdp",
    "unemployment", "nonfarm", "non-farm", "opec", "eia",
    "federal reserve", "bank of england", "bank of japan", "ecb",
    "unexpected", "surprise", "beats forecast", "misses forecast",
    "above expectations", "below expectations", "war", "sanction",
    "bitcoin etf", "ethereum etf", "halving", "institutional"
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

sent_headlines = set()


# ─────────────────────────────────────────────
# CORE FUNCTIONS
# ─────────────────────────────────────────────

def keep_render_awake():
    """Ping Render server every 10 mins to prevent free tier sleep"""
    try:
        response = requests.get(f"{RENDER_URL}/", timeout=10)
        logging.info(f"Keep-alive ping → status {response.status_code}")
    except Exception as e:
        logging.warning(f"Keep-alive ping failed: {e}")


def is_noise(headline: str) -> bool:
    text = headline.lower()
    return any(phrase in text for phrase in NOISE_PHRASES)


def get_pair_relevance_score(headline: str, pair: str) -> float:
    config  = PAIR_CONFIG.get(pair, {})
    text    = headline.lower()

    excludes = config.get("exclude", [])
    if any(ex in text for ex in excludes):
        return 0.0

    primary   = config.get("primary", [])
    secondary = config.get("secondary", [])

    primary_matches   = sum(1 for kw in primary if kw in text)
    secondary_matches = sum(1 for kw in secondary if kw in text)

    if primary_matches == 0 and secondary_matches == 0:
        return 0.0

    if primary_matches > 0:
        score = min((primary_matches * 1.0 + secondary_matches * 0.4) / 2.0, 1.0)
    else:
        score = min(secondary_matches * 0.4 / 2.0, 0.5)

    return round(score, 2)


def get_affected_pairs(headline: str) -> dict:
    return {
        pair: score
        for pair in PAIR_CONFIG
        if (score := get_pair_relevance_score(headline, pair)) > 0
    }


def score_sentiment(headline: str) -> tuple:
    text    = headline.lower()
    bullish = sum(1 for w in BULLISH_WORDS if w in text)
    bearish = sum(1 for w in BEARISH_WORDS if w in text)
    total   = bullish + bearish

    if total == 0:
        return "NEUTRAL", 0.5
    if bullish > bearish:
        return "BULLISH", round(0.5 + (bullish / total - 0.5) * 0.8, 2)
    elif bearish > bullish:
        return "BEARISH", round(0.5 + (bearish / total - 0.5) * 0.8, 2)
    return "NEUTRAL", 0.5


def calculate_impact_probability(headline: str, relevance_score: float, confidence: float) -> int:
    text    = headline.lower()
    trigger = min(sum(0.1 for t in HIGH_IMPACT_TRIGGERS if t in text), 0.35)
    raw     = (relevance_score * 0.5) + (confidence * 0.25) + trigger
    return max(int(min(raw * 100, 97)), 10)


def get_impact_duration(headline: str) -> tuple:
    text = headline.lower()
    for triggers, label, hours in DURATION_RULES:
        if any(t in text for t in triggers):
            return label, hours
    return DEFAULT_DURATION


def get_sentiment_emoji(label: str) -> str:
    return {"BULLISH": "📈", "BEARISH": "📉", "NEUTRAL": "➡️"}.get(label, "➡️")


def get_impact_emoji(prob: int) -> str:
    return "🔴" if prob >= 75 else "🟡" if prob >= 55 else "🟢"


def get_duration_emoji(hours: int) -> str:
    return "⏳" if hours >= 48 else "🕐" if hours >= 6 else "⚡"


def fetch_rss(url: str, source: str) -> list:
    headlines = []
    try:
        r    = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        for item in soup.find_all("item")[:20]:
            title = item.find("title")
            if title:
                text = re.sub(r"<!\[CDATA\[|\]\]>", "", title.get_text(strip=True)).strip()
                if len(text) >= MIN_HEADLINE_LENGTH:
                    headlines.append({"text": text, "source": source})
        logging.info(f"{source}: {len(headlines)} headlines")
    except Exception as e:
        logging.warning(f"{source} failed: {e}")
    return headlines


def send_telegram(message: str):
    for chunk in [message[i:i+4000] for i in range(0, len(message), 4000)]:
        try:
            requests.post(TELEGRAM_URL, json={
                "chat_id":    TELEGRAM_CHAT_ID,
                "text":       chunk,
                "parse_mode": "HTML"
            }, timeout=10).raise_for_status()
        except Exception as e:
            logging.error(f"Telegram error: {e}")


def run_market_scan(session_label: str = ""):
    logging.info(f"Starting market scan — {session_label}")

    all_headlines = []
    all_headlines += fetch_rss("https://www.forexlive.com/feed/news",             "ForexLive")
    all_headlines += fetch_rss("https://www.fxstreet.com/rss/news",               "FXStreet")
    all_headlines += fetch_rss("https://www.investing.com/rss/news_285.rss",      "Investing.com")
    all_headlines += fetch_rss("https://oilprice.com/rss/main",                   "OilPrice")
    all_headlines += fetch_rss("https://feeds.reuters.com/reuters/businessNews",  "Reuters")
    all_headlines += fetch_rss("https://cointelegraph.com/rss",                   "CoinTelegraph")
    all_headlines += fetch_rss("https://decrypt.co/feed",                         "Decrypt")

    logging.info(f"Total gathered: {len(all_headlines)}")

    scored = []
    for item in all_headlines:
        headline = item["text"]
        source   = item["source"]

        if headline in sent_headlines:
            continue
        if is_noise(headline):
            continue

        pair_relevance = get_affected_pairs(headline)
        if not pair_relevance:
            continue

        label, confidence       = score_sentiment(headline)
        duration_label, dur_hrs = get_impact_duration(headline)

        pair_impacts = {
            pair: calculate_impact_probability(headline, rel_score, confidence)
            for pair, rel_score in pair_relevance.items()
        }
        pair_impacts = {p: v for p, v in pair_impacts.items() if v >= MIN_IMPACT_THRESHOLD}

        if not pair_impacts:
            continue

        scored.append({
            "headline":       headline,
            "source":         source,
            "sentiment":      label,
            "confidence":     confidence,
            "pairs":          pair_impacts,
            "max_prob":       max(pair_impacts.values()),
            "duration_label": duration_label,
            "duration_hours": dur_hrs,
        })
        sent_headlines.add(headline)

    scored.sort(key=lambda x: x["max_prob"], reverse=True)
    top = scored[:MAX_HEADLINES_PER_REPORT]

    if not top:
        logging.info("No relevant headlines this scan — skipping Telegram")
        return

    now   = datetime.now(timezone.utc).strftime("%H:%M UTC")
    label = f" — {session_label}" if session_label else ""

    parts = [
        f"🌐 <b>Market Intelligence{label}</b>",
        f"🕐 {now}  |  {len(top)} relevant headlines",
        "━━━━━━━━━━━━━━━━━━━━",
    ]

    for i, item in enumerate(top, 1):
        dur_e      = get_duration_emoji(item["duration_hours"])
        pairs_text = "\n".join(
            f"   {get_impact_emoji(prob)} <b>{pair}</b>: {prob}% impact probability"
            for pair, prob in sorted(item["pairs"].items(), key=lambda x: x[1], reverse=True)
        )
        parts.append(
            f"\n<b>{i}. {item['headline']}</b>\n"
            f"📌 {item['source']}\n"
            f"{get_sentiment_emoji(item['sentiment'])} <b>{item['sentiment']}</b> "
            f"({int(item['confidence'] * 100)}% confidence)\n"
            f"{dur_e} Effect lasts: ~<b>{item['duration_label']}</b>\n"
            f"{pairs_text}"
        )
        parts.append("━━━━━━━━━━━━━━━━━━━━")

    parts.append(
        "\n🔴 High (75%+)  🟡 Medium (55–74%)  🟢 Lower (40–54%)\n"
        "⏳ Long lasting  🕐 Medium  ⚡ Short lived"
    )

    send_telegram("\n".join(parts))
    logging.info(f"Sent {len(top)} headlines")


def run_scheduler():
    print("=" * 60)
    print("  Market Intelligence Scraper (Render Edition)")
    print("=" * 60)
    print("  Pairs   : GBPUSD, GBPJPY, XAUUSD, XAGUSD,")
    print("            BTCUSD, ETHUSD, US Oil, NAS100, GER40")
    print("  Sources : ForexLive, FXStreet, Investing.com,")
    print("            OilPrice, Reuters, CoinTelegraph, Decrypt")
    print("  Scans   : 6x daily at optimal session times (UTC)")
    print(f"  Keep-alive → {RENDER_URL}")
    print("=" * 60)

    # Optimal market session scans
    schedule.every().day.at("06:00").do(run_market_scan, session_label="Pre-London")
    schedule.every().day.at("08:00").do(run_market_scan, session_label="London Open")
    schedule.every().day.at("12:00").do(run_market_scan, session_label="London/NY Overlap")
    schedule.every().day.at("15:00").do(run_market_scan, session_label="NY Session")
    schedule.every().day.at("19:00").do(run_market_scan, session_label="NY Close")
    schedule.every().day.at("22:00").do(run_market_scan, session_label="Asian Open")

    # Keep Render server awake every 10 mins
    schedule.every(10).minutes.do(keep_render_awake)

    # Run scan immediately on startup
    run_market_scan(session_label="Startup")
    keep_render_awake()

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    run_scheduler()
