import yt_dlp
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, MessageHandler, CallbackQueryHandler, filters, ContextTypes
)
import os
import threading
import asyncio

# Flask app
app = Flask(__name__)

# Replace with your bot token
BOT_TOKEN = "7926753627:AAG5LRHiRrzRvKcFXGOOVGo5CdDKFYm8Ync"

# Path to the cookies.txt file
COOKIES_PATH = os.path.join(os.path.dirname(__file__), "cookies.txt")

# Maintain user states for ongoing interactions
user_states = {}

# Map resolutions to quality labels
QUALITY_LABELS = {
    "144p": "Low Quality",
    "240p": "Medium Quality",
    "360p": "Medium Quality",
    "480p": "High Quality",
    "720p": "HD Quality",
    "1080p": "Full HD Quality",
}

# Initialize the Telegram bot
application = Application.builder().token(BOT_TOKEN).build()

@app.route("/")
def home():
    return "Bot is running!"

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id
    url = update.message.text.strip()

    if not url.startswith("http://") and not url.startswith("https://"):
        await update.message.reply_text("Please send a valid YouTube URL.")
        return

    try:
        message = await update.message.reply_text("Processing your URL...")
        ydl_opts = {
            "quiet": True,
            "cookiefile": COOKIES_PATH,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = info.get("formats", [])

            available_formats = [
                fmt for fmt in formats if fmt.get("acodec") != "none" or fmt.get("vcodec") != "none"
            ]

            if not available_formats:
                await message.edit_text("No suitable formats found for the provided URL.")
                return

            user_states[user_id] = {"url": url, "formats": available_formats}

            keyboard = [
                [
                    InlineKeyboardButton(
                        f"{QUALITY_LABELS.get(fmt.get('resolution', 'audio only'), 'Unknown Quality')} - {fmt.get('resolution', 'audio only')} ({fmt.get('ext')})",
                        callback_data=f"quality_{fmt.get('format_id')}",
                    )
                ]
                for fmt in available_formats
            ]

            reply_markup = InlineKeyboardMarkup(keyboard)
            await message.edit_text("Choose a quality to get the download link:", reply_markup=reply_markup)

    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

async def handle_quality_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.message.chat_id
    if user_id not in user_states:
        await query.edit_message_text("Session expired. Please send a new URL.")
        return

    data = query.data
    format_id = data.split("_")[1]
    formats = user_states[user_id]["formats"]

    selected_format = next((fmt for fmt in formats if fmt["format_id"] == format_id), None)
    if not selected_format:
        await query.edit_message_text("Error: Selected format not found.")
        return

    download_url = selected_format.get("url")
    if not download_url:
        await query.edit_message_text("Error: Unable to retrieve the download URL.")
        return

    await query.edit_message_text(f"Here is your download link:\n{download_url}")

def start_flask():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

def start_telegram_bot():
    application.run_polling()

if __name__ == "__main__":
    # Run Flask in a separate thread
    flask_thread = threading.Thread(target=start_flask)
    flask_thread.start()

    # Run Telegram bot in the main thread
    start_telegram_bot()
