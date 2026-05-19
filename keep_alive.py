# ============================================================
# keep_alive.py — Keeps the bot running 24/7 on Render
#
# Render puts free apps to sleep if they don't get web traffic.
# This file runs a tiny web server in the background of the bot.
# When a service like UptimeRobot pings this web server,
# it keeps the bot awake and running.
# ============================================================

from flask import Flask
from threading import Thread

# Create a Flask web app
app = Flask('')

@app.route('/')
def home():
    # This is what shows when you open the bot's URL in a browser
    return "✅ Bot is online and running!"

def run():
    # Run the web server on port 8080 (Render's default or custom port)
    # 0.0.0.0 means it accepts connections from the internet
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    # Start the web server in a separate thread (in the background)
    # so it doesn't block the Discord bot from running.
    server_thread = Thread(target=run)
    server_thread.start()
