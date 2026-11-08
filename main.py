import os
import threading
from flask import Flask
import telebot
import yfinance as yf

# 1. Mini web server for Render keep-alive
app = Flask(__name__)

@app.route('/')
def home():
    return "Amine Finance Alert is running 24/7!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# 2. Telegram Bot Configuration
TOKEN = os.environ.get("TELEGRAM_TOKEN")
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = (
        "📈 **Welcome to Amine Finance Alert!**\n\n"
        "Available commands:\n"
        "• `/sp500` : Get current S&P 500 price\n"
        "• `/price SYMBOL` : Get stock/ETF price (e.g. `/price AAPL` or `/price NVDA`)\n"
    )
    bot.reply_to(message, welcome_text, parse_mode="Markdown")

@bot.message_handler(commands=['sp500'])
def get_sp500(message):
    try:
        sp = yf.Ticker("^GSPC").history(period="1d")
        price = sp['Close'].iloc[-1]
        bot.reply_to(message, f"📊 **S&P 500** : `{price:.2f} USD`", parse_mode="Markdown")
    except Exception:
        bot.reply_to(message, "⚠️ Error fetching S&P 500 index price.")

@bot.message_handler(commands=['price', 'prix'])
def get_price(message):
    try:
        symbol = message.text.split()[1].upper()
        ticker = yf.Ticker(symbol).history(period="1d")
        if ticker.empty:
            bot.reply_to(message, f"❌ Ticker symbol '{symbol}' not found.")
            return
        price = ticker['Close'].iloc[-1]
        bot.reply_to(message, f"📈 **{symbol}** : `{price:.2f}`", parse_mode="Markdown")
    except IndexError:
        bot.reply_to(message, "⚠️ Please specify a symbol. Example: `/price AAPL` or `/price NVDA`.")
    except Exception:
        bot.reply_to(message, "⚠️ Error fetching price data.")

# 3. Launch server & polling
if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    bot.infinity_polling()
