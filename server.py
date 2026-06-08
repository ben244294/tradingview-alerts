"""
TradingView Alert Server
========================
Receives webhooks from TradingView and sends push notifications
to your Telegram via your personal bot.

Deploy this file to Render (cloud).
"""

from flask import Flask, request, jsonify
import requests
import json
import logging

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────
TELEGRAM_TOKEN   = "8282705170:AAHM0iAJ50WESe79IZMUyxXAg5aUc9q7Gno"
TELEGRAM_CHAT_ID = "7936995648"
TELEGRAM_URL     = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

WEBHOOK_SECRET   = "gallop123"   # ← Change this to any password you like
# ─────────────────────────────────────────────

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def send_telegram(message: str):
    """Send a message to your Telegram bot"""
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"   # Allows <b>bold</b> and <i>italic</i> in messages
    }
    try:
        response = requests.post(TELEGRAM_URL, json=payload, timeout=10)
        response.raise_for_status()
        logging.info("Telegram message sent successfully")
    except Exception as e:
        logging.error(f"Failed to send Telegram message: {e}")


@app.route("/webhook", methods=["POST"])
def webhook():
    """Main endpoint — TradingView posts alerts here"""

    # Security check
    secret = request.args.get("secret", "")
    if secret != WEBHOOK_SECRET:
        logging.warning("Rejected webhook — wrong secret")
        return jsonify({"error": "Unauthorized"}), 401

    try:
        body = request.get_data(as_text=True)
        logging.info(f"Received webhook: {body}")

        # Try parsing as JSON first
        try:
            data = json.loads(body)
            alert_type = data.get("type", "alert")
            pair       = data.get("pair", "Unknown")
            message    = data.get("message", body)
        except json.JSONDecodeError:
            alert_type = "alert"
            pair       = "Market"
            message    = body

        # Route to the right notification style
        if alert_type == "candle_close":
            send_telegram(
                f"🕯️ <b>4H Candle Closed — {pair}</b>\n\n{message}"
            )

        elif alert_type == "news":
            send_telegram(
                f"📰 <b>News Alert — {pair}</b>\n\n{message}"
            )

        else:
            send_telegram(
                f"🔔 <b>TradingView Alert — {pair}</b>\n\n{message}"
            )

        return jsonify({"status": "ok"}), 200

    except Exception as e:
        logging.error(f"Webhook error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/test", methods=["GET"])
def test():
    """Visit this URL in your browser to test Telegram is working"""
    send_telegram(
        "✅ <b>Server is working!</b>\n\nYour TradingView alert server is connected and ready."
    )
    return "Test message sent! Check your Telegram.", 200


@app.route("/", methods=["GET"])
def home():
    return "TradingView Alert Server is running ✅", 200


if __name__ == "__main__":
    print("=" * 50)
    print("  TradingView Alert Server (Telegram Edition)")
    print("=" * 50)
    print(f"  Telegram Chat ID : {TELEGRAM_CHAT_ID}")
    print(f"  Webhook URL      : http://localhost:5000/webhook?secret={WEBHOOK_SECRET}")
    print(f"  Test URL         : http://localhost:5000/test")
    print("=" * 50)
    app.run(host="0.0.0.0", port=5000, debug=False)
