"""
Economic Calendar Poller
========================
Checks for upcoming high-impact news events affecting your pairs
every 5 minutes and sends advance warnings via Telegram.

Deployed to Render as a background worker — no laptop needed!

Pairs monitored: GBPUSD, US Oil, GBPJPY, NAS100, German 40 (DAX)
"""

import requests
import time
import schedule
import logging
from datetime import datetime, timezone, timedelta

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────
TELEGRAM_TOKEN   = "8282705170:AAHM0iAJ50WESe79IZMUyxXAg5aUc9q7Gno"
TELEGRAM_CHAT_ID = "7936995648"
TELEGRAM_URL     = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

# Ghana/Accra is UTC+0
UTC_OFFSET_HOURS = 0
TIMEZONE_LABEL   = "Accra (UTC+0)"

# Warn this many minutes before a news event
WARN_MINUTES_BEFORE = 30
# ─────────────────────────────────────────────

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

PAIR_CURRENCIES = {
    "GBPUSD":    ["GBP", "USD"],
    "GBPJPY":    ["GBP", "JPY"],
    "US Oil":    ["USD"],
    "NAS100":    ["USD"],
    "German 40": ["EUR"],
}

WATCHED_CURRENCIES = {"GBP", "USD", "JPY", "EUR"}
alerted_events = set()

EVENT_CONTEXT = {
    "Non-Farm Employment Change": "new jobs added in the US (excl. farming)",
    "CPI m/m": "monthly change in consumer prices (inflation)",
    "CPI y/y": "annual change in consumer prices (inflation)",
    "Core CPI m/m": "inflation excluding food & energy",
    "Interest Rate Decision": "central bank decision on borrowing costs",
    "GDP m/m": "monthly economic growth",
    "GDP q/q": "quarterly economic growth",
    "Unemployment Rate": "percentage of workforce without jobs",
    "Retail Sales m/m": "monthly change in consumer spending",
    "PMI": "business activity — above 50 = expansion",
    "FOMC Statement": "US Federal Reserve policy statement",
    "Crude Oil Inventories": "weekly US oil supply data",
}


def get_event_context(title: str) -> str:
    for key, desc in EVENT_CONTEXT.items():
        if key.lower() in title.lower():
            return f"\n📖 <i>{desc}</i>"
    return ""


def format_value(value: str, label: str) -> str:
    if not value or value.strip() == "":
        return f"{label}: <i>N/A</i>"
    return f"{label}: <b>{value}</b>"


def send_telegram(message: str):
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(TELEGRAM_URL, json=payload, timeout=10)
        response.raise_for_status()
        logging.info("Telegram message sent successfully")
    except Exception as e:
        logging.error(f"Failed to send Telegram message: {e}")


def get_pairs_for_currency(currency: str) -> list:
    return [pair for pair, currencies in PAIR_CURRENCIES.items() if currency in currencies]


def get_local_time(utc_time: datetime) -> str:
    local_time = utc_time + timedelta(hours=UTC_OFFSET_HOURS)
    return local_time.strftime("%H:%M")


def fetch_economic_calendar() -> list:
    url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        events = response.json()
        logging.info(f"Fetched {len(events)} events from calendar")
        return events
    except Exception as e:
        logging.error(f"Failed to fetch calendar: {e}")
        return []


def check_upcoming_events():
    logging.info("Checking economic calendar...")
    events = fetch_economic_calendar()
    if not events:
        return

    now = datetime.now(timezone.utc)

    for event in events:
        try:
            event_time_str = event.get("date", "")
            if not event_time_str:
                continue

            event_time = datetime.fromisoformat(event_time_str.replace("Z", "+00:00"))

            if event.get("impact", "").lower() != "high":
                continue

            currency = event.get("country", "").upper()
            if currency not in WATCHED_CURRENCIES:
                continue

            minutes_until = (event_time - now).total_seconds() / 60

            if 0 <= minutes_until <= WARN_MINUTES_BEFORE:
                event_id = f"{event_time_str}_{event.get('title', '')}"

                if event_id not in alerted_events:
                    alerted_events.add(event_id)

                    affected_pairs = get_pairs_for_currency(currency)
                    pairs_str      = ", ".join(affected_pairs) if affected_pairs else currency
                    time_str       = get_local_time(event_time)
                    event_title    = event.get("title", "Unknown Event")
                    forecast       = event.get("forecast", "").strip()
                    previous       = event.get("previous", "").strip()
                    context        = get_event_context(event_title)

                    message = (
                        f"🚨 <b>HIGH IMPACT NEWS in {int(minutes_until)} mins</b>\n"
                        f"━━━━━━━━━━━━━━━━━━━━\n"
                        f"📌 <b>{event_title}</b>{context}\n\n"
                        f"💱 <b>Currency:</b> {currency}\n"
                        f"🕐 <b>Time:</b> {time_str} ({TIMEZONE_LABEL})\n"
                        f"📊 <b>Affects:</b> {pairs_str}\n\n"
                        f"━━━━━━━━━━━━━━━━━━━━\n"
                        f"📈 {format_value(forecast, 'Forecast')}\n"
                        f"📉 {format_value(previous, 'Previous')}\n"
                        f"━━━━━━━━━━━━━━━━━━━━\n"
                        f"⚠️ <i>Consider managing open positions on {pairs_str}</i>"
                    )
                    send_telegram(message)

        except Exception as e:
            logging.warning(f"Skipped event: {e}")


def send_daily_preview():
    logging.info("Sending daily preview...")
    events = fetch_economic_calendar()

    now = datetime.now(timezone.utc)
    today_str = now.strftime("%Y-%m-%d")

    today_events = []
    for event in events:
        try:
            event_time_str = event.get("date", "")
            event_time = datetime.fromisoformat(event_time_str.replace("Z", "+00:00"))
            local_time = event_time + timedelta(hours=UTC_OFFSET_HOURS)

            if local_time.strftime("%Y-%m-%d") != today_str:
                continue
            if event.get("impact", "").lower() != "high":
                continue

            currency = event.get("country", "").upper()
            if currency not in WATCHED_CURRENCIES:
                continue

            affected_pairs = get_pairs_for_currency(currency)
            time_str = local_time.strftime("%H:%M")
            forecast = event.get("forecast", "").strip()
            previous = event.get("previous", "").strip()

            today_events.append(
                f"🕐 <b>{time_str}</b> | {currency} | <b>{event.get('title', '?')}</b>\n"
                f"   → Pairs: {', '.join(affected_pairs)}\n"
                f"   → Forecast: <b>{forecast or 'N/A'}</b> | Previous: <b>{previous or 'N/A'}</b>"
            )
        except Exception:
            continue

    day_str = (now + timedelta(hours=UTC_OFFSET_HOURS)).strftime("%A %d %b")

    if today_events:
        events_text = "\n\n".join(today_events)
        message = f"📅 <b>Daily Preview — {day_str}</b>\n━━━━━━━━━━━━━━━━━━━━\n\n{events_text}"
    else:
        message = f"📅 <b>Daily Preview — {day_str}</b>\n\nNo high-impact events today for your pairs. Clean day to trade! ✅"

    send_telegram(message)


def run_scheduler():
    print("=" * 50)
    print("  Economic Calendar Poller (Render Edition)")
    print("=" * 50)
    print(f"  Timezone      : {TIMEZONE_LABEL}")
    print(f"  Warn before   : {WARN_MINUTES_BEFORE} minutes")
    print(f"  Telegram ID   : {TELEGRAM_CHAT_ID}")
    print("=" * 50)
    print("  Scheduler running. Press Ctrl+C to stop.\n")

    schedule.every(5).minutes.do(check_upcoming_events)
    schedule.every().day.at("07:00").do(send_daily_preview)

    # Run immediately on startup
    check_upcoming_events()
    send_daily_preview()

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    run_scheduler()
