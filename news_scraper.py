"""
Market Intelligence Scraper
============================
Scrapes financial news headlines every 2 hours, scores them
with sentiment analysis, calculates impact probability per pair,
and sends a formatted breakdown to Telegram.

Pairs monitored: GBPUSD, GBPJPY, US Oil, NAS100, German 40

Deploy to Railway as a background worker.
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
TELEGRAM_TOKEN   = "8282705170:AAHM0iAJ50WESe79IZMUyxXAg5aUc9q7Gno"
TELEGRAM_CHAT_ID = "7936995648"
TELEGRAM_URL     = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

MIN_IMPACT_THRESHOLD    = 40   # minimum % to include in report
MAX_HEADLINES_PER_REPORT = 8   # max headlines per scan
# ─────────────────────────────────────────────

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

PAIR_KEYWORDS = {
    "GBPUSD": [
        "bank of england", "boe", "uk inflation", "uk cpi", "uk gdp",
        "uk economy", "pound", "sterling", "gbp", "uk interest rate",
        "uk unemployment", "fed", "federal reserve", "fomc", "us cpi",
        "us inflation", "us jobs", "nonfarm", "non-farm", "dollar", "usd",
        "us gdp", "us economy", "us interest rate", "us recession"
    ],
    "GBPJPY": [
        "bank of england", "boe", "uk inflation", "uk cpi", "pound",
        "sterling", "gbp", "bank of japan", "boj", "japan inflation",
        "japan gdp", "yen", "jpy", "japanese economy", "japan interest rate",
        "japan cpi", "tokyo cpi", "japan recession"
    ],
    "US Oil": [
        "oil", "crude", "wti", "brent", "opec", "eia", "energy",
        "petroleum", "oil inventory", "oil supply", "oil demand",
        "oil production", "oil price", "barrel", "gasoline",
        "natural gas", "energy prices", "oil reserves", "oil cut"
    ],
    "NAS100": [
        "nasdaq", "nas100", "tech stocks", "federal reserve", "fed",
        "fomc", "us interest rate", "us inflation", "us cpi", "us gdp",
        "us economy", "apple", "microsoft", "nvidia", "google", "amazon",
        "meta", "tech earnings", "rate hike", "rate cut", "powell",
        "ai stocks", "semiconductor"
    ],
    "German 40": [
        "dax", "german 40", "ecb", "european central bank", "eurozone",
        "euro", "eur", "germany", "german economy", "german gdp",
        "german inflation", "german cpi", "eu inflation", "eurozone cpi",
        "eurozone gdp", "lagarde", "eu economy", "ifo", "europe recession"
    ],
}

sent_headlines = set()

BULLISH_WORDS = [
    "rise", "rises", "rose", "surges", "jumps", "gains", "rallies",
    "beats", "exceeds", "strong", "stronger", "growth", "grows",
    "higher", "increase", "hawkish", "rate hike", "positive",
    "optimistic", "recovery", "recovers", "boost", "above expectations",
    "better than expected", "record high", "expansion", "upbeat", "solid", "robust"
]

BEARISH_WORDS = [
    "fall", "falls", "fell", "drops", "plunges", "slides", "misses",
    "weak", "weaker", "slowdown", "slows", "lower", "decrease",
    "dovish", "rate cut", "negative", "pessimistic", "recession",
    "contracts", "below expectations", "worse than expected",
    "record low", "contraction", "concern", "warning", "crisis", "turmoil"
]

HIGH_IMPACT_TRIGGERS = [
    "interest rate", "rate decision", "inflation", "cpi", "gdp",
    "unemployment", "nonfarm", "non-farm", "opec", "eia",
    "federal reserve", "bank of england", "bank of japan", "ecb",
    "emergency", "crisis", "record", "unexpected", "surprise",
    "beats", "misses", "above expectations", "below expectations"
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def score_sentiment(headline: str) -> tuple:
    """
    Keyword-based sentiment scorer.
    Returns (label, confidence): label = BULLISH/BEARISH/NEUTRAL
    confidence = 0.0 to 1.0

    NOTE: Replace with FinBERT after completing Hugging Face course:
    from transformers import pipeline
    finbert = pipeline("text-classification", model="yiyanghkust/finbert-tone")
    result = finbert(headline)[0]
    label_map = {"Positive": "BULLISH", "Negative": "BEARISH", "Neutral": "NEUTRAL"}
    return label_map[result["label"]], round(result["score"], 2)
    """
    text = headline.lower()
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


def get_affected_pairs(headline: str) -> list:
    text = headline.lower()
    return [pair for pair, kws in PAIR_KEYWORDS.items() if any(kw in text for kw in kws)]


def calculate_impact_probability(headline: str, pair: str, confidence: float) -> int:
    text     = headline.lower()
    keywords = PAIR_KEYWORDS.get(pair, [])
    matches  = sum(1 for kw in keywords if kw in text)
    kw_score = min(matches / 3, 1.0)
    trigger  = min(sum(0.1 for t in HIGH_IMPACT_TRIGGERS if t in text), 0.3)
    raw      = (kw_score * 0.5) + (confidence * 0.3) + trigger
    return max(int(min(raw * 100, 97)), 10)


def get_sentiment_emoji(label: str) -> str:
    return {"BULLISH": "📈", "BEARISH": "📉", "NEUTRAL": "➡️"}.get(label, "➡️")


def get_impact_emoji(prob: int) -> str:
    return "🔴" if prob >= 75 else "🟡" if prob >= 55 else "🟢"


def fetch_rss(url: str, source: str) -> list:
    """Generic RSS fetcher used by all sources"""
    headlines = []
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        for item in soup.find_all("item")[:15]:
            title = item.find("title")
            if title:
                text = re.sub(r"<!\[CDATA\[|\]\]>", "", title.get_text(strip=True)).strip()
                if len(text) > 20:
                    headlines.append({"text": text, "source": source})
        logging.info(f"{source}: {len(headlines)} headlines")
    except Exception as e:
        logging.warning(f"{source} failed: {e}")
    return headlines


def send_telegram(message: str):
    for chunk in [message[i:i+4000] for i in range(0, len(message), 4000)]:
        try:
            requests.post(TELEGRAM_URL, json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": chunk,
                "parse_mode": "HTML"
            }, timeout=10).raise_for_status()
        except Exception as e:
            logging.error(f"Telegram error: {e}")


def run_market_scan():
    logging.info("Starting market intelligence scan...")

    all_headlines = []
    all_headlines += fetch_rss("https://www.forexlive.com/feed/news",         "ForexLive")
    all_headlines += fetch_rss("https://www.fxstreet.com/rss/news",           "FXStreet")
    all_headlines += fetch_rss("https://www.investing.com/rss/news_285.rss",  "Investing.com")
    all_headlines += fetch_rss("https://oilprice.com/rss/main",               "OilPrice")
    all_headlines += fetch_rss("https://feeds.reuters.com/reuters/businessNews", "Reuters")

    logging.info(f"Total gathered: {len(all_headlines)}")

    scored = []
    for item in all_headlines:
        headline = item["text"]
        source   = item["source"]

        if headline in sent_headlines:
            continue

        affected = get_affected_pairs(headline)
        if not affected:
            continue

        label, confidence = score_sentiment(headline)

        pair_impacts = {
            pair: calculate_impact_probability(headline, pair, confidence)
            for pair in affected
        }
        pair_impacts = {p: v for p, v in pair_impacts.items() if v >= MIN_IMPACT_THRESHOLD}

        if not pair_impacts:
            continue

        scored.append({
            "headline":   headline,
            "source":     source,
            "sentiment":  label,
            "confidence": confidence,
            "pairs":      pair_impacts,
            "max_prob":   max(pair_impacts.values()),
        })
        sent_headlines.add(headline)

    scored.sort(key=lambda x: x["max_prob"], reverse=True)
    top = scored[:MAX_HEADLINES_PER_REPORT]

    if not top:
        send_telegram(
            "🌐 <b>Market Intelligence Scan</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "No significant headlines found this scan. ✅"
        )
        return

    now   = datetime.now(timezone.utc).strftime("%H:%M UTC")
    parts = [
        f"🌐 <b>Market Intelligence Report</b>",
        f"🕐 {now}  |  {len(top)} relevant headlines",
        "━━━━━━━━━━━━━━━━━━━━",
    ]

    for i, item in enumerate(top, 1):
        pairs_text = "\n".join(
            f"   {get_impact_emoji(prob)} <b>{pair}</b>: {prob}% impact probability"
            for pair, prob in sorted(item["pairs"].items(), key=lambda x: x[1], reverse=True)
        )
        parts.append(
            f"\n<b>{i}. {item['headline']}</b>\n"
            f"📌 {item['source']}\n"
            f"{get_sentiment_emoji(item['sentiment'])} Sentiment: <b>{item['sentiment']}</b> "
            f"({int(item['confidence'] * 100)}% confidence)\n"
            f"{pairs_text}"
        )
        parts.append("━━━━━━━━━━━━━━━━━━━━")

    parts.append("\n🔴 High (75%+)  🟡 Medium (55–74%)  🟢 Lower (40–54%)")
    send_telegram("\n".join(parts))
    logging.info(f"Scan complete — {len(top)} headlines sent")


def run_scheduler():
    print("=" * 55)
    print("  Market Intelligence Scraper")
    print("=" * 55)
    print("  Pairs   : GBPUSD, GBPJPY, US Oil, NAS100, GER40")
    print("  Sources : ForexLive, FXStreet, Investing, OilPrice, Reuters")
    print("  Every   : 2 hours")
    print("=" * 55)

    schedule.every(2).hours.do(run_market_scan)
    run_market_scan()

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    run_scheduler()
