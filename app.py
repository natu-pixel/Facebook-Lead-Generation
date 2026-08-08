from flask import Flask, jsonify
import threading
import os
import bot_listener

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({
        "status": "running",
        "bot": "active",
        "description": "Geoapify Lead Generation Telegram Bot Listener"
    })

def start_bot():
    try:
        bot_listener.main()
    except Exception as e:
        print(f"Error running bot listener thread: {str(e)}")

# Start the Telegram bot polling loop in a background thread when the server runs
bot_thread = threading.Thread(target=start_bot, daemon=True)
bot_thread.start()

if __name__ == '__main__':
    # Koyeb and Render dynamically assign a port via the PORT environment variable
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
