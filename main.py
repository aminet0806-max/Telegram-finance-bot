import os
import threading
from flask import Flask
import telebot
import yfinance as yf
from apscheduler.schedulers.background import BackgroundScheduler

# 1. Web server for Render keep-alive
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
subscribers = set()
alert_sent_today = False

def send_daily_briefing():
    global alert_sent_today
    alert_sent_today = False  # Reset DCA alert flag for the new day
    if not subscribers:
        return
    try:
        sp = yf.Ticker("^GSPC").history(period="2d")
        nasdaq = yf.Ticker("^IXIC").history(period="2d")
        cac = yf.Ticker("^FCHI").history(period="2d")
        btc = yf.Ticker("BTC-USD").history(period="1d")

        sp_price = sp['Close'].iloc[-1]
        sp_prev = sp['Close'].iloc[-2] if len(sp) > 1 else sp_price
        sp_change = ((sp_price - sp_prev) / sp_prev) * 100

        nasdaq_price = nasdaq['Close'].iloc[-1]
        nasdaq_prev = nasdaq['Close'].iloc[-2] if len(nasdaq) > 1 else nasdaq_price
        nasdaq_change = ((nasdaq_price - nasdaq_prev) / nasdaq_prev) * 100

        cac_price = cac['Close'].iloc[-1]
        cac_prev = cac['Close'].iloc[-2] if len(cac) > 1 else cac_price
        cac_change = ((cac_price - cac_prev) / cac_prev) * 100

        btc_price = btc['Close'].iloc[-1]

        sp_icon = "🟢" if sp_change >= 0 else "🔴"
        nasdaq_icon = "🟢" if nasdaq_change >= 0 else "🔴"
        cac_icon = "🟢" if cac_change >= 0 else "🔴"

        briefing_text = (
            "☀️ **Daily Morning Market Briefing** ☀️\n\n"
            f"📊 **S&P 500**: `{sp_price:.2f} USD` ({sp_icon} {sp_change:+.2f}%)\n"
            f"💻 **Nasdaq**: `{nasdaq_price:.2f} USD` ({nasdaq_icon} {nasdaq_change:+.2f}%)\n"
            f"🇫🇷 **CAC 40**: `{cac_price:.2f} EUR` ({cac_icon} {cac_change:+.2f}%)\n"
            f"🪙 **Bitcoin**: `{btc_price:.2f} USD`\n\n"
            "Have a great trading day! 🚀"
        )

        for chat_id in list(subscribers):
            try:
                bot.send_message(chat_id, briefing_text, parse_mode="Markdown")
            except Exception:
                pass
    except Exception as e:
        print(f"Error fetching briefing data: {e}")

def check_dca_alerts():
    global alert_sent_today
    if not subscribers or alert_sent_today:
        return
    try:
        sp = yf.Ticker("^GSPC").history(period="2d")
        if len(sp) > 1:
            sp_price = sp['Close'].iloc[-1]
            sp_prev = sp['Close'].iloc[-2]
            sp_change = ((sp_price - sp_prev) / sp_prev) * 100

            # Trigger DCA Alert if S&P 500 drops >= 1.5%
            if sp_change <= -1.5:
                alert_sent_today = True
                alert_text = (
                    "🚨 **DCA OPPORTUNITY ALERT** 🚨\n\n"
                    f"📉 **S&P 500** dropped `{sp_change:.2f}%` today!\n"
                    f"Current Price: `{sp_price:.2f} USD`\n\n"
                    "💡 *Market dips can present strategic Dollar-Cost Averaging opportunities.*"
                )
                for chat_id in list(subscribers):
                    try:
                        bot.send_message(chat_id, alert_text, parse_mode="Markdown")
                    except Exception:
                        pass
    except Exception as e:
        print(f"Error checking DCA alert: {e}")

# Scheduler setup (Europe/Paris timezone)
scheduler = BackgroundScheduler(timezone="Europe/Paris")
scheduler.add_job(send_daily_briefing, 'cron', hour=8, minute=0)
scheduler.add_job(check_dca_alerts, 'interval', minutes=30)
scheduler.start()

@bot.message_handler(commands=['start'])
def send_welcome(message):
    subscribers.add(message.chat.id)
    welcome_text = (
        "📈 **Welcome to Amine Finance Alert!**\n\n"
        " You are registered for **Daily Briefings (8:00 AM)** & **DCA Dip Alerts**!\n\n"
        "Available commands:\n"
        "• `/sp500` : Get S&P 500 index price\n"
        "• `/nasdaq` : Get Nasdaq Composite price\n"
        "• `/cac40` : Get CAC 40 index price\n"
        "• `/btc` : Get Bitcoin price\n"
        "• `/price SYMBOL` : Get stock/ETF price (e.g. `/price AAPL` or `/price NVDA`)\n"
        "• `/briefing` : Get daily market briefing immediately\n"
    )
    bot.reply_to(message, welcome_text, parse_mode="Markdown")

@bot.message_handler(commands=['briefing'])
def trigger_briefing(message):
    subscribers.add(message.chat.id)
    bot.reply_to(message, "🔄 Fetching market briefing...")
    send_daily_briefing()

def fetch_index(message, symbol, name, currency):
    try:
        ticker = yf.Ticker(symbol).history(period="2d")
        price = ticker['Close'].iloc[-1]
        prev = ticker['Close'].iloc[-2] if len(ticker) > 1 else price
        change = ((price - prev) / prev) * 100
        icon = "🟢" if change >= 0 else "🔴"
        bot.reply_to(message, f"📊 **{name}** : `{price:.2f} {currency}` ({icon} {change:+.2f}%)", parse_mode="Markdown")
    except Exception:
        bot.reply_to(message, f"⚠️ Error fetching {name} price.")

@bot.message_handler(commands=['sp500'])
def get_sp500(message):
    subscribers.add(message.chat.id)
    fetch_index(message, "^GSPC", "S&P 500", "USD")

@bot.message_handler(commands=['nasdaq'])
def get_nasdaq(message):
    subscribers.add(message.chat.id)
    fetch_index(message, "^IXIC", "Nasdaq", "USD")

@bot.message_handler(commands=['cac40'])
def get_cac40(message):
    subscribers.add(message.chat.id)
    fetch_index(message, "^FCHI", "CAC 40", "EUR")

@bot.message_handler(commands=['btc'])
def get_btc(message):
    subscribers.add(message.chat.id)
    fetch_index(message, "BTC-USD", "Bitcoin", "USD")

@bot.message_handler(commands=['price', 'prix'])
def get_price(message):
    subscribers.add(message.chat.id)
    try:
        symbol = message.text.split()[1].upper()
        ticker = yf.Ticker(symbol).history(period="2d")
        if ticker.empty:
            bot.reply_to(message, f"❌ Ticker symbol '{symbol}' not found.")
            return
        price = ticker['Close'].iloc[-1]
        prev = ticker['Close'].iloc[-2] if len(ticker) > 1 else price
        change = ((price - prev) / prev) * 100
        icon = "🟢" if change >= 0 else "🔴"
        bot.reply_to(message, f"📈 **{symbol}** : `{price:.2f}` ({icon} {change:+.2f}%)", parse_mode="Markdown")
    except IndexError:
        bot.reply_to(message, "⚠️ Please specify a symbol. Example: `/price AAPL` or `/price NVDA`.")
    except Exception:
        bot.reply_to(message, "⚠️ Error fetching price data.")

# 3. Launch server & polling
if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    bot.infinity_polling()
