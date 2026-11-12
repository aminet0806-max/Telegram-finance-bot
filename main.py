import os
import threading
from flask import Flask
import telebot
import yfinance as yf
import feedparser
from apscheduler.schedulers.background import BackgroundScheduler

# 1. Serveur Web pour UptimeRobot
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is alive!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# 2. Configuration du Bot + Ton ID permanent
TOKEN = os.environ.get("TELEGRAM_TOKEN")
MY_ID = os.environ.get("MY_CHAT_ID")
bot = telebot.TeleBot(TOKEN)
subscribers = set()

if MY_ID:
    subscribers.add(int(MY_ID))

alert_sent_today = False

def get_asset_data(symbol):
    ticker = yf.Ticker(symbol).history(period="2d")
    if ticker.empty:
        return None, None
    price = ticker['Close'].iloc[-1]
    prev = ticker['Close'].iloc[-2] if len(ticker) > 1 else price
    change = ((price - prev) / prev) * 100
    return price, change

def format_line(label, price, change, unit=""):
    if price is None:
        return f"{label}: `N/A`\n"
    trend = "🟢" if change >= 0 else "🔴"
    return f"{label}: `{price:.2f}{unit}` ({trend} {change:+.2f}%)\n"

def fetch_news(limit=3):
    urls = [
        "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=20910258",
        "https://feeds.bbci.co.uk/news/world/rss.xml"
    ]
    headlines = []
    for url in urls:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:2]:
                headlines.append(f"• [{entry.title}]({entry.link})")
        except Exception:
            continue
    return "\n".join(headlines[:limit]) if headlines else "• No news right now."

def send_daily_briefing():
    global alert_sent_today
    alert_sent_today = False
    if not subscribers:
        return

    sp_p, sp_c = get_asset_data("^GSPC")
    nq_p, nq_c = get_asset_data("^IXIC")
    cac_p, cac_c = get_asset_data("^FCHI")
    btc_p, btc_c = get_asset_data("BTC-USD")
    silver_p, silver_c = get_asset_data("SI=F")
    gold_p, gold_c = get_asset_data("GC=F")
    us10y_p, us10y_c = get_asset_data("^TNX")
    vix_p, vix_c = get_asset_data("^VIX")
    news_block = fetch_news(limit=3)

    text = (
        "☀️ **DAILY MACRO & MARKET BRIEFING** ☀️\n\n"
        "**📈 MARKETS**\n"
        + format_line("📊 **S&P 500**", sp_p, sp_c, " USD")
        + format_line("💻 **Nasdaq**", nq_p, nq_c, " USD")
        + format_line("🇫🇷 **CAC 40**", cac_p, cac_c, " EUR")
        + format_line("🪙 **Bitcoin**", btc_p, btc_c, " USD")
        + "\n**🌐 MACRO & METALS**\n"
        + format_line("🥈 **Silver**", silver_p, silver_c, " USD")
        + format_line("🥇 **Gold**", gold_p, gold_c, " USD")
        + format_line("🇺🇸 **US 10Y**", us10y_p, us10y_c, "%")
        + format_line("⚡ **VIX**", vix_p, vix_c, "")
        + f"\n**🌍 GEOPOLITICS & MACRO NEWS**\n{news_block}\n\n"
        "Have a great trading day! 🚀"
    )

    for chat_id in list(subscribers):
        try:
            bot.send_message(chat_id, text, parse_mode="Markdown", disable_web_page_preview=True)
        except Exception:
            pass

def check_dca_alerts():
    global alert_sent_today
    if not subscribers or alert_sent_today:
        return
    sp_p, sp_c = get_asset_data("^GSPC")
    if sp_c is not None and sp_c <= -1.5:
        alert_sent_today = True
        text = (
            "🚨 **DCA OPPORTUNITY ALERT** 🚨\n\n"
            f"📉 **S&P 500** dropped `{sp_c:.2f}%` today (`{sp_p:.2f} USD`)!"
        )
        for chat_id in list(subscribers):
            try:
                bot.send_message(chat_id, text, parse_mode="Markdown")
            except Exception:
                pass

# Envoi automatique tous les jours à 8h00 (Paris)
scheduler = BackgroundScheduler(timezone="Europe/Paris")
scheduler.add_job(send_daily_briefing, 'cron', hour=8, minute=0)
scheduler.add_job(check_dca_alerts, 'interval', minutes=30)
scheduler.start()

@bot.message_handler(commands=['start'])
def send_welcome(message):
    subscribers.add(message.chat.id)
    bot.reply_to(message, "✅ **Bot Active!** You will receive your Daily Macro Briefing at 8:00 AM.", parse_mode="Markdown")

@bot.message_handler(commands=['macro'])
def get_macro(message):
    subscribers.add(message.chat.id)
    silver_p, silver_c = get_asset_data("SI=F")
    gold_p, gold_c = get_asset_data("GC=F")
    us10y_p, us10y_c = get_asset_data("^TNX")
    dxy_p, dxy_c = get_asset_data("DX-Y.NYB")
    oil_p, oil_c = get_asset_data("CL=F")
    vix_p, vix_c = get_asset_data("^VIX")

    text = (
        "🌐 **GLOBAL MACRO & METALS**\n\n"
        + format_line("🥈 **Silver**", silver_p, silver_c, " USD")
        + format_line("🥇 **Gold**", gold_p, gold_c, " USD")
        + format_line("🇺🇸 **US 10Y**", us10y_p, us10y_c, "%")
        + format_line("💵 **DXY Dollar**", dxy_p, dxy_c, "")
        + format_line("🛢️ **Oil WTI**", oil_p, oil_c, " USD")
        + format_line("⚡ **VIX**", vix_p, vix_c, "")
    )
    bot.reply_to(message, text, parse_mode="Markdown")

@bot.message_handler(commands=['news'])
def get_news(message):
    subscribers.add(message.chat.id)
    bot.reply_to(message, f"🌍 **LATEST NEWS**\n\n{fetch_news(limit=5)}", parse_mode="Markdown", disable_web_page_preview=True)

@bot.message_handler(commands=['briefing'])
def trigger_briefing(message):
    subscribers.add(message.chat.id)
    send_daily_briefing()

@bot.message_handler(commands=['sp500'])
def get_sp500(message):
    p, c = get_asset_data("^GSPC")
    bot.reply_to(message, format_line("📊 **S&P 500**", p, c, " USD"), parse_mode="Markdown")

@bot.message_handler(commands=['nasdaq'])
def get_nasdaq(message):
    p, c = get_asset_data("^IXIC")
    bot.reply_to(message, format_line("💻 **Nasdaq**", p, c, " USD"), parse_mode="Markdown")

@bot.message_handler(commands=['cac40'])
def get_cac40(message):
    p, c = get_asset_data("^FCHI")
    bot.reply_to(message, format_line("🇫🇷 **CAC 40**", p, c, " EUR"), parse_mode="Markdown")

@bot.message_handler(commands=['btc'])
def get_btc(message):
    p, c = get_asset_data("BTC-USD")
    bot.reply_to(message, format_line("🪙 **Bitcoin**", p, c, " USD"), parse_mode="Markdown")

@bot.message_handler(commands=['price', 'prix'])
def get_price(message):
    try:
        symbol = message.text.split()[1].upper()
        p, c = get_asset_data(symbol)
        bot.reply_to(message, format_line(f"📈 **{symbol}**", p, c, ""), parse_mode="Markdown")
    except Exception:
        bot.reply_to(message, "⚠️ Example: `/price NVDA` or `/price SI=F`")

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    bot.infinity_polling()
