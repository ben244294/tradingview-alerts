"""
TradingView Alert Server
========================
Receives webhooks from TradingView and sends push notifications
to your Android phone via ntfy.sh (free, no account needed).

Run this on your Windows laptop, then expose it using ngrok.
"""

from flask import Flask, request, jsonify
import requests
import json
import logging

# ─────────────────────────────────────────────
# CONFIGURATION — edit these values
# ─────────────────────────────────────────────
NTFY_TOPIC = "Essibo_alerts"   # ← Change this to something unique!
                                           #   Use a random string so only you get it
                                           #   e.g. "james-trading-9472"

NTFY_URL = f"https://ntfy.sh/{NTFY_TOPIC}"

WEBHOOK_SECRET = "Thepasswordis@2"      # ← Set this in TradingView webhook URL too
                                           #   e.g. http://yourngrok.com/webhook?secret=my_secret_key_123
# ─────────────────────────────────────────────

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def send_notification(title: str, message: str, priority: str = "default", tags: list = None):
    """Send a push notification to your Android phone via ntfy.sh"""
    headers = {
        "Title": title,
        "Priority": priority,        # min / low / default / high / urgent
        "Tags": ",".join(tags or [])
    }
    try:
        response = requests.post(NTFY_URL, data=message.encode("utf-8"), headers=headers, timeout=10)
        response.raise_for_status()
        logging.info(f"Notification sent: {title}")
    except Exception as e:
        logging.error(f"Failed to send notification: {e}")


@app.route("/webhook", methods=["POST"])
def webhook():
    """Main endpoint — TradingView posts alerts here"""

    # Optional secret check for security
    secret = request.args.get("secret", "")
    if secret != WEBHOOK_SECRET:
        logging.warning("Rejected webhook — wrong secret")
        return jsonify({"error": "Unauthorized"}), 401

    # Parse the alert message from TradingView
    # TradingView sends either plain text or JSON in the body
    try:
        body = request.get_data(as_text=True)
        logging.info(f"Received webhook: {body}")

        # Try parsing as JSON first
        try:
            data = json.loads(body)
            alert_type = data.get("type", "alert")
            pair = data.get("pair", "Unknown")
            message = data.get("message", body)
            timeframe = data.get("timeframe", "")
        except json.JSONDecodeError:
            # Plain text alert from TradingView
            alert_type = "alert"
            pair = "Market"
            message = body
            timeframe = ""

        # Route to the right notification style
        if alert_type == "candle_close":
            send_notification(
                title=f"🕯️ 4H Candle Closed — {pair}",
                message=f"{pair} 4-hour candle has closed.\n{message}",
                priority="default",
                tags=["chart_increasing"]
            )

        elif alert_type == "news":
            send_notification(
                title=f"📰 News Alert — {pair}",
                message=message,
                priority="high",
                tags=["newspaper", "warning"]
            )

        else:
            # Generic alert fallback
            send_notification(
                title=f"🔔 TradingView Alert — {pair}",
                message=message,
                priority="default",
                tags=["bell"]
            )

        return jsonify({"status": "ok"}), 200

    except Exception as e:
        logging.error(f"Webhook error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/test", methods=["GET"])
def test():
    """Visit this URL in your browser to test notifications are working"""
    send_notification(
        title="✅ Server is working!",
        message="Your TradingView alert server is connected and ready.",
        priority="default",
        tags=["white_check_mark"]
    )
    return "Test notification sent! Check your phone.", 200


@app.route("/", methods=["GET"])
def home():
    return "TradingView Alert Server is running ✅", 200


if __name__ == "__main__":
    print("=" * 50)
    print("  TradingView Alert Server")
    print("=" * 50)
    print(f"  Notifications → ntfy.sh/{NTFY_TOPIC}")
    print(f"  Webhook URL   → http://localhost:5000/webhook?secret={WEBHOOK_SECRET}")
    print(f"  Test URL      → http://localhost:5000/test")
    print("=" * 50)
    app.run(host="0.0.0.0", port=5000, debug=False)
