"""
TradingView Alert Server
========================
Receives webhooks from TradingView and sends push notifications
to your Telegram via your personal bot.

Deployed on Render as a Web Service.
"""

from flask import Flask, request, jsonify
import requests
import json
import logging
import os

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────
TELEGRAM_TOKEN   = "8282705170:AAHM0iAJ50WESe79IZMUyxXAg5aUc9q7Gno"
TELEGRAM_CHAT_ID = "7936995648"
TELEGRAM_URL     = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
WEBHOOK_SECRET   = "Thepasswordis@2"
# ─────────────────────────────────────────────

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def send_telegram(message: str):
    """Send a message to your Telegram bot"""
    payload = {
        "chat_id":    TELEGRAM_CHAT_ID,
        "text":       message,
        "parse_mode": "HTML"
    }
    try:
        requests.post(TELEGRAM_URL, json=payload, timeout=10).raise_for_status()
        logging.info("Telegram message sent successfully")
    except Exception as e:
        logging.error(f"Failed to send Telegram message: {e}")


@app.route("/webhook", methods=["POST"])
def webhook():
    """Main endpoint — TradingView posts alerts here"""
    secret = request.args.get("secret", "")
    if secret != WEBHOOK_SECRET:
        logging.warning("Rejected webhook — wrong secret")
        return jsonify({"error": "Unauthorized"}), 401

    try:
        body = request.get_data(as_text=True)
        logging.info(f"Received webhook: {body}")

        try:
            data       = json.loads(body)
            alert_type = data.get("type", "alert")
            pair       = data.get("pair", "Unknown")
            message    = data.get("message", body)
        except json.JSONDecodeError:
            alert_type = "alert"
            pair       = "Market"
            message    = body

        if alert_type == "candle_close":
            send_telegram(f"🕯️ <b>4H Candle Closed — {pair}</b>\n\n{message}")
        elif alert_type == "news":
            send_telegram(f"📰 <b>News Alert — {pair}</b>\n\n{message}")
        else:
            send_telegram(f"🔔 <b>TradingView Alert — {pair}</b>\n\n{message}")

        return jsonify({"status": "ok"}), 200

    except Exception as e:
        logging.error(f"Webhook error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/test", methods=["GET"])
def test():
    """Visit this URL in your browser to test Telegram is working"""
    send_telegram(
        "✅ <b>Server is working!</b>\n\n"
        "Your TradingView alert server is connected and ready."
    )
    return "Test message sent! Check your Telegram.", 200


@app.route("/", methods=["GET"])
def home():
    """Keep-alive endpoint — pinged by calendar_poller and news_scraper"""
    return "TradingView Alert Server is running ✅", 200


if __name__ == "__main__":
    print("=" * 50)
    print("  TradingView Alert Server (Telegram Edition)")
    print("=" * 50)
    print(f"  Telegram Chat ID : {TELEGRAM_CHAT_ID}")
    print(f"  Webhook URL      : /webhook?secret={WEBHOOK_SECRET}")
    print(f"  Test URL         : /test")
    print("=" * 50)
    # Use Render's PORT environment variable, fallback to 5000 locally
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
