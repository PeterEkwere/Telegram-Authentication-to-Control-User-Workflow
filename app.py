import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from dotenv import load_dotenv

load_dotenv()  # Load environment variables

app = Flask(__name__)
CORS(app, origins=["http://18.144.169.247:3000"])
TELEGRAM_API = f"https://api.telegram.org/bot{os.getenv('TELEGRAM_BOT_TOKEN')}/sendMessage"


@app.route('/notify', methods=['POST'])
def notify():
    print("Notify WAS TRIGGERED")
    data = request.json
    print(f"DATA IS {data}")
    ip = request.remote_addr  # Basic IP detection (may not be accurate)
    print(f"IP IS {ip}")

    # Send message to Telegram
    message = f"New User Visited!\nIP: {ip}\nLocation: {get_location(ip)}"
    payload = {
        "chat_id": os.getenv('TELEGRAM_CHAT_ID'),
        "text": message
    }
    requests.post(TELEGRAM_API, json=payload)
    return jsonify({"status": "success"})


def get_location(ip):
    # Simple IP location lookup (replace with better service if needed)
    try:
        response = requests.get(f"http://ip-api.com/json/{ip}?fields=country,city")
        location = response.json()
        return f"{location.get('city', 'Unknown')}, {location.get('country', 'Unknown')}"
    except:
        return "Location unavailable"


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
