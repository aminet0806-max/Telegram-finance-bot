import os
import json
import threading
from flask import Flask
import telebot
import yfinance as yf
import feedparser
from apscheduler.schedulers.background import BackgroundScheduler

# 1. Web server for Render keep-alive
app = Flask(__name__)

@app.route('/')
def home():
    return "Amine Finance Alert is running 24/7!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# 2. Telegram Bot & Persistent Subscribers
TOKEN = os.environ.get("TELEGRAM_TOKEN")
bot = telebot.TeleBot(TOKEN)
SUBS_FILE = "subscribers.json"

def load_subscribers():
    if os.path.exists(SUBS_FILE):
        try:
            with open(SUBS_FILE, "r") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()

def save_subscriber(chat_id):
    subscribers.add(chat_id)
    try:
        with open(SUBS_FILE, "w") as f:
            json.dump(list(subscribers), f)
    except Exception:
        pass

subscribers = load_subscribers()
alert_sent_today = False

# Helper function to fetch price & daily % change
def get_asset_data(symbol):
    ticker = yf.Ticker(symbol).history(period="2d")
    if ticker.empty:
        return None, None
    price = ticker['Close'].iloc[-1]
    prev = ticker['Close'].iloc[-2] if len(ticker) > 1 else price
    change = ((price - prev) / prev) * 100
    return price, change

def format_line(icon_label, price, change, unit=""):
    if price is None:
        return f"{icon_label}: `N/A`\n"
    trend = "🟢" if change >= 0 else "🔴"
    return f"{icon_label}: `{price:.2f}{unit}` ({trend} {change:+.2f}%)\n"

# Fetch top 3 Macro/Geopolitics headlines via RSS
def fetch_geopolitics_news(limit=3):
    rss_urls = [
        "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=20910258", # CNBC Economy
        "https://feeds.bbci.co.uk/news/world/rss.xml" # BBC World Geopolitics
    ]
    headlines = []
    for url in rss_urls:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:2]:
                headlines.append(f"• [{entry.title}]({entry.link})")
        except Exception:
            continue
    return "\n".join(headlines[:limit]) if headlines else "• No major news fetched right now."

def send_daily_briefing():
    global alert_sent_today
    alert_sent_today = False
    if not subscribers:
        return

    sp_p, sp_c = get_asset_data("^GSPC")
    nq_p, nq_c = get_asset_data("^IXIC")
    cac_p, cac_c = get_asset_data("^FCHI")
    btc_p, btc_c = get_asset_data("BTC-USD")
    
    # Macro & Metals
    gold_p, gold_c = get_asset_data("GC=F")
    silver_p, silver_c = get_asset_data("SI=F")
    us10y_p, us10y_c = get_asset_data("^TNX")
    vix_p, vix_c = get_asset_data("^VIX")

    news_block = fetch_geopolitics_news(limit=3)

    briefing_text = (
        "☀️ **DAILY MACRO & MARKET BRIEFING** ☀️\n\n"
        "**📈 EQUITIES & CRYPTO**\n"
        + format_line("📊 **S&P 500**", sp_p, sp_c, " USD")
        + format_line("💻 **Nasdaq**", nq_p, nq_c, " USD")
        + format_line("🇫🇷 **CAC 40**", cac_p, cac_c, " EUR")
        + format_line("🪙 **Bitcoin**", btc_p, btc_c, " USD")
        + "\n**🌐 MACRO, METALS & VOLATILITY**\n"
        + format_line("🥈 **Silver**", silver_p, silver_c, " USD")
        + format_line("🥇 **Gold**", gold_p, gold_c, " USD")
        + format_line("🇺🇸 **US 10Y Yield**", us10y_p, us10y_c, "%")
        + format_line("⚡ **VIX (Fear)**", vix_p, vix_c, "")
        + f"\n**🌍 GEOPOLITICS & MACRO HEADLINES**\n{news_block}\n\n"
        "Have a sharp trading day! 🚀"
    )

    for chat_id in list(subscribers):
        try:
            bot.send_message(chat_id, briefing_text, parse_mode="Markdown", disable_web_page_preview=True)
        except Exception:
            pass

def check_dca_alerts():
    global alert_sent_today
    if not subscribers or alert_sent_today:
        return
    sp_p, sp_c = get_asset_data("^GSPC")
    if sp_c is not None and sp_c <= -1.5:
        alert_sent_today = True
        alert_text = (
            "🚨 **DCA OPPORTUNITY ALERT** 🚨\n\n"
            f"📉 **S&P 500** dropped `{sp_c:.2f}%` today (`{sp_p:.2f} USD`)!\n"
            "💡 *Strategic Dollar-Cost Averaging window.*"
        )
        for chat_id in list(subscribers):
            try:
                bot.send_message(chat_id, alert_text, parse_mode="Markdown")
            except Exception:
                pass

# Scheduler (8:00 AM Paris time)
scheduler = BackgroundScheduler(timezone="Europe/Paris")
scheduler.add_job(send_daily_briefing, 'cron', hour=8, minute=0)
scheduler.add_job(check_dca_alerts, 'interval', minutes=30)
scheduler.start()

# Bot Commands
@bot.message_handler(commands=['start'])
def send_welcome(message):
    save_subscriber(message.chat.id)
    welcome_text = (
        "📈 **Welcome to Amine Finance Alert!**\n\n"
        "You are subscribed to the **8:00 AM Macro & Geopolitics Briefing** & **DCA Alerts**.\n\n"
        "**Commands:**\n"
        "• `/macro` : Silver, Gold, US 10Y, DXY, Oil & VIX\n"
        "• `/news` : Live Geopolitics & Macro headlines\n"
        "• `/briefing` : Trigger full morning briefing now\n"
        "• `/sp500`, `/nasdaq`, `/cac40`, `/btc`\n"
        "• `/price SYMBOL` : Any stock/ETF/commodity\n"
    )
    bot.reply_to(message, welcome_text, parse_mode="Markdown")

@bot.message_handler(commands=['macro'])
def get_macro(message):
    save_subscriber(message.chat.id)
    silver_p, silver_c = get_asset_data("SI=F")
    gold_p, gold_c = get_asset_data("GC=F")
    us10y_p, us10y_c = get_asset_data("^TNX")
    dxy_p, dxy_c = get_asset_data("DX-Y.NYB")
    oil_p, oil_c = get_asset_data("CL=F")
    vix_p, vix_c = get_asset_data("^VIX")

    macro_text = (
        "🌐 **GLOBAL MACRO & COMMODITIES**\n\n"
        + format_line("🥈 **Silver (XAG)**", silver_p, silver_c, " USD")
        + format_line("🥇 **Gold (XAU)**", gold_p, gold_c, " USD")
        + format_line("🇺🇸 **US 10Y Yield**", us10y_p, us10y_c, "%")
        + format_line("💵 **Dollar Index (DXY)**", dxy_p, dxy_c, "")
        + format_line("🛢️ **Crude Oil (WTI)**", oil_p, oil_c, " USD")
        + format_line("⚡ **VIX Volatility**", vix_p, vix_c, "")
    )
    bot.reply_to(message, macro_text, parse_mode="Markdown")

@bot.message_handler(commands=['news'])
def get_news(message):
    save_subscriber(message.chat.id)
    news_block = fetch_geopolitics_news(limit=5)
    bot.reply_to(message, f"🌍 **LATEST MACRO & GEOPOLITICS NEWS**\n\n{news_block}", parse_mode="Markdown", disable_web_page_preview=True)

@bot.message_handler(commands=['briefing'])
def trigger_briefing(message):
    save_subscriber(message.chat.id)
    bot.reply_to(message, "🔄 Compiling Macro, Metals & Geopolitics briefing...")
    send_daily_briefing()

def send_single_index(message, symbol, name, currency):
    save_subscriber(message.chat.id)
    p, c = get_asset_data(symbol)
    if p is None:
        bot.reply_to(message, f"⚠️ Error fetching {name}.")
    else:
        bot.reply_to(message, format_line(f"📊 **{name}**", p, c, f" {currency}"), parse_mode="Markdown")

@bot.message_handler(commands=['sp500'])
def get_sp500(message):
    send_single_index(message, "^GSPC", "S&P 500", "USD")

@bot.message_handler(commands=['nasdaq'])
def get_nasdaq(message):
    send_single_index(message, "^IXIC", "Nasdaq", "USD")

@bot.message_handler(commands=['cac40'])
def get_cac40(message):
    send_single_index(message, "^FCHI", "CAC 40", "EUR")

@bot.message_handler(commands=['btc'])
def get_btc(message):
    send_single_index(message, "BTC-USD", "Bitcoin", "USD")

@bot.message_handler(commands=['price', 'prix'])
def get_price(message):
    save_subscriber(message.chat.id)
    try:
        symbol = message.text.split()[1].upper()
        p, c = get_asset_data(symbol)
        if p is None:
            bot.reply_to(message, f"❌ Ticker '{symbol}' not found.")
        else:
            bot.reply_to(message, format_line(f"📈 **{symbol}**", p, c, ""), parse_mode="Markdown")
    except IndexError:
        bot.reply_to(message, "⚠️ Specify a symbol. Example: `/price SI=F` or `/price NVDA`.")

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    bot.infinity_polling()
