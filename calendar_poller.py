"""
Economic Calendar Poller
========================
- Warns 30 mins before high-impact events (with forecast & previous)
- Sends actual data release after the event fires
- Compares actual vs forecast and gives a reaction signal
- Daily 7am briefing
- Deployed to Railway as a background worker
"""

import requests
import time
import schedule
import logging
import re
from datetime import datetime, timezone, timedelta

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────
TELEGRAM_TOKEN   = "8282705170:AAHM0iAJ50WESe79IZMUyxXAg5aUc9q7Gno"
TELEGRAM_CHAT_ID = "7936995648"
TELEGRAM_URL     = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

UTC_OFFSET_HOURS    = 0
TIMEZONE_LABEL      = "Accra (UTC+0)"
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

alerted_events  = set()
pending_actuals = {}

EVENT_CONTEXT = {
    "Non-Farm Employment Change": "new jobs added in the US (excl. farming)",
    "CPI m/m":                    "monthly change in consumer prices (inflation)",
    "CPI y/y":                    "annual change in consumer prices (inflation)",
    "Core CPI m/m":               "inflation excluding food & energy",
    "Interest Rate Decision":     "central bank decision on borrowing costs",
    "GDP m/m":                    "monthly economic growth",
    "GDP q/q":                    "quarterly economic growth",
    "Unemployment Rate":          "percentage of workforce without jobs",
    "Retail Sales m/m":           "monthly change in consumer spending",
    "PMI":                        "business activity — above 50 = expansion",
    "FOMC Statement":             "US Federal Reserve policy statement",
    "Crude Oil Inventories":      "weekly US oil supply data",
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


def get_reaction_signal(actual: str, forecast: str, previous: str, currency: str) -> str:
    """
    Compare actual vs forecast to generate a directional reaction signal.
    Higher than forecast = bullish for that currency in most cases.
    """
    if not actual or actual.strip() == "":
        return ""

    def clean(val):
        return float(re.sub(r"[%KMBkmb,\s]", "", val.strip()))

    try:
        actual_f   = clean(actual)
        forecast_f = clean(forecast) if forecast and forecast.strip() else None
        previous_f = clean(previous) if previous and previous.strip() else None

        if forecast_f is not None:
            diff = actual_f - forecast_f
            if diff > 0:
                return f"📈 <b>BEATS FORECAST</b> by {abs(diff):.2f} → Bullish {currency}"
            elif diff < 0:
                return f"📉 <b>MISSES FORECAST</b> by {abs(diff):.2f} → Bearish {currency}"
            else:
                return f"➡️ <b>IN LINE</b> with forecast → Neutral {currency}"

        elif previous_f is not None:
            if actual_f > previous_f:
                return f"📈 <b>HIGHER</b> than previous → Bullish {currency}"
            elif actual_f < previous_f:
                return f"📉 <b>LOWER</b> than previous → Bearish {currency}"
            else:
                return f"➡️ <b>SAME</b> as previous → Neutral {currency}"

    except Exception:
        pass

    return ""


def send_telegram(message: str):
    payload = {
        "chat_id":    TELEGRAM_CHAT_ID,
        "text":       message,
        "parse_mode": "HTML"
    }
    try:
        requests.post(TELEGRAM_URL, json=payload, timeout=10).raise_for_status()
        logging.info("Telegram message sent")
    except Exception as e:
        logging.error(f"Telegram error: {e}")


def get_pairs_for_currency(currency: str) -> list:
    return [p for p, cs in PAIR_CURRENCIES.items() if currency in cs]


def get_local_time(utc_time: datetime) -> str:
    return (utc_time + timedelta(hours=UTC_OFFSET_HOURS)).strftime("%H:%M")


def fetch_economic_calendar() -> list:
    url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        events = r.json()
        logging.info(f"Fetched {len(events)} events")
        return events
    except Exception as e:
        logging.error(f"Calendar fetch failed: {e}")
        return []


def check_upcoming_events():
    """Warn 30 mins before high-impact events with forecast & previous"""
    logging.info("Checking upcoming events...")
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
                event_id = f"warn_{event_time_str}_{event.get('title', '')}"

                if event_id not in alerted_events:
                    alerted_events.add(event_id)

                    pairs     = get_pairs_for_currency(currency)
                    pairs_str = ", ".join(pairs) if pairs else currency
                    time_str  = get_local_time(event_time)
                    title     = event.get("title", "Unknown Event")
                    forecast  = event.get("forecast", "").strip()
                    previous  = event.get("previous", "").strip()
                    context   = get_event_context(title)

                    message = (
                        f"🚨 <b>HIGH IMPACT NEWS in {int(minutes_until)} mins</b>\n"
                        f"━━━━━━━━━━━━━━━━━━━━\n"
                        f"📌 <b>{title}</b>{context}\n\n"
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

                    # Queue for actual data check after event fires
                    actual_id = f"actual_{event_time_str}_{event.get('title', '')}"
                    if actual_id not in pending_actuals:
                        pending_actuals[actual_id] = {
                            "title":      title,
                            "currency":   currency,
                            "event_time": event_time,
                            "forecast":   forecast,
                            "previous":   previous,
                            "pairs_str":  pairs_str,
                        }

        except Exception as e:
            logging.warning(f"Event error: {e}")


def check_actual_releases():
    """
    Poll calendar every 5 mins after event time.
    As soon as 'actual' value appears in the feed, send it
    with a reaction signal comparing actual vs forecast.
    """
    if not pending_actuals:
        return

    logging.info(f"Checking actuals for {len(pending_actuals)} pending events...")
    events = fetch_economic_calendar()
    if not events:
        return

    now       = datetime.now(timezone.utc)
    to_remove = []

    for event_id, queued in list(pending_actuals.items()):
        event_time = queued["event_time"]

        # Only check events that have already passed
        if now < event_time:
            continue

        # Give up after 3 hours
        if (now - event_time).total_seconds() > 10800:
            to_remove.append(event_id)
            continue

        for event in events:
            try:
                et_str     = event.get("date", "")
                if not et_str:
                    continue

                feed_time   = datetime.fromisoformat(et_str.replace("Z", "+00:00"))
                title_match = event.get("title", "") == queued["title"]
                time_match  = abs((feed_time - event_time).total_seconds()) < 60

                if not (title_match and time_match):
                    continue

                actual = event.get("actual", "").strip()

                if actual and actual != "":
                    forecast  = queued["forecast"]
                    previous  = queued["previous"]
                    currency  = queued["currency"]
                    title     = queued["title"]
                    pairs_str = queued["pairs_str"]
                    time_str  = get_local_time(event_time)
                    context   = get_event_context(title)
                    reaction  = get_reaction_signal(actual, forecast, previous, currency)

                    message = (
                        f"📊 <b>ACTUAL DATA RELEASED</b>\n"
                        f"━━━━━━━━━━━━━━━━━━━━\n"
                        f"📌 <b>{title}</b>{context}\n\n"
                        f"💱 <b>Currency:</b> {currency}\n"
                        f"🕐 <b>Released:</b> {time_str} ({TIMEZONE_LABEL})\n"
                        f"📊 <b>Affects:</b> {pairs_str}\n\n"
                        f"━━━━━━━━━━━━━━━━━━━━\n"
                        f"🎯 {format_value(actual,   'Actual')}\n"
                        f"📈 {format_value(forecast, 'Forecast')}\n"
                        f"📉 {format_value(previous, 'Previous')}\n"
                        f"━━━━━━━━━━━━━━━━━━━━\n"
                    )

                    if reaction:
                        message += f"⚡ <b>Reaction Signal:</b> {reaction}\n"
                        message += f"━━━━━━━━━━━━━━━━━━━━\n"

                    message += f"👁 <i>Watch {pairs_str} for immediate price reaction</i>"

                    send_telegram(message)
                    to_remove.append(event_id)
                    break

            except Exception as e:
                logging.warning(f"Actual check error: {e}")

    for eid in to_remove:
        pending_actuals.pop(eid, None)


def send_daily_preview():
    """7am daily briefing with all high-impact events for today"""
    logging.info("Sending daily preview...")
    events    = fetch_economic_calendar()
    now       = datetime.now(timezone.utc)
    today_str = (now + timedelta(hours=UTC_OFFSET_HOURS)).strftime("%Y-%m-%d")
    day_str   = (now + timedelta(hours=UTC_OFFSET_HOURS)).strftime("%A %d %b")

    today_events = []
    for event in events:
        try:
            et_str   = event.get("date", "")
            et       = datetime.fromisoformat(et_str.replace("Z", "+00:00"))
            local_et = et + timedelta(hours=UTC_OFFSET_HOURS)

            if local_et.strftime("%Y-%m-%d") != today_str:
                continue
            if event.get("impact", "").lower() != "high":
                continue

            currency = event.get("country", "").upper()
            if currency not in WATCHED_CURRENCIES:
                continue

            pairs    = get_pairs_for_currency(currency)
            time_str = local_et.strftime("%H:%M")
            forecast = event.get("forecast", "").strip()
            previous = event.get("previous", "").strip()

            today_events.append(
                f"🕐 <b>{time_str}</b> | {currency} | <b>{event.get('title', '?')}</b>\n"
                f"   → Pairs: {', '.join(pairs)}\n"
                f"   → Forecast: <b>{forecast or 'N/A'}</b> | Previous: <b>{previous or 'N/A'}</b>"
            )
        except Exception:
            continue

    if today_events:
        message = (
            f"📅 <b>Daily Preview — {day_str}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            + "\n\n".join(today_events)
        )
    else:
        message = (
            f"📅 <b>Daily Preview — {day_str}</b>\n\n"
            f"No high-impact events today for your pairs. Clean day to trade! ✅"
        )

    send_telegram(message)


def run_scheduler():
    print("=" * 50)
    print("  Economic Calendar Poller (with Actuals)")
    print("=" * 50)
    print(f"  Timezone  : {TIMEZONE_LABEL}")
    print(f"  Warning   : {WARN_MINUTES_BEFORE} mins before event")
    print(f"  Actuals   : polled every 5 mins after release")
    print("=" * 50)

    # Check for upcoming warnings every 5 mins
    schedule.every(5).minutes.do(check_upcoming_events)

    # Check for actual data releases every 5 mins
    schedule.every(5).minutes.do(check_actual_releases)

    # Daily 7am briefing
    schedule.every().day.at("07:00").do(send_daily_preview)

    # Run immediately on startup
    check_upcoming_events()
    send_daily_preview()

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    run_scheduler()
