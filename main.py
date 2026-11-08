import os
import threading
from flask import Flask
import telebot
import yfinance as yf

# 1. Mini serveur web pour Render
app = Flask(__name__)

@app.route('/')
def home():
    return "Amine Finance Alert is running 24/7!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# 2. Configuration du Bot Telegram
TOKEN = os.environ.get("TELEGRAM_TOKEN")
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = (
        "📈 **Bienvenue sur Amine Finance Alert !**\n\n"
        "Commandes disponibles :\n"
        "• `/sp500` : Obtenir le cours actuel du S&P 500\n"
        "• `/prix SYMBOLE` : Obtenir le cours d'une action/ETF (ex: `/prix AAPL` ou `/prix MC.PA`)\n"
    )
    bot.reply_to(message, welcome_text, parse_mode="Markdown")

@bot.message_handler(commands=['sp500'])
def get_sp500(message):
    try:
        sp = yf.Ticker("^GSPC").history(period="1d")
        prix = sp['Close'].iloc[-1]
        bot.reply_to(message, f"📊 **S&P 500** : `{prix:.2f} USD`", parse_mode="Markdown")
    except Exception:
        bot.reply_to(message, "⚠️ Erreur lors de la récupération du cours du S&P 500.")

@bot.message_handler(commands=['prix'])
def get_price(message):
    try:
        symbol = message.text.split()[1].upper()
        ticker = yf.Ticker(symbol).history(period="1d")
        if ticker.empty:
            bot.reply_to(message, f"❌ Symbole '{symbol}' introuvable.")
            return
        prix = ticker['Close'].iloc[-1]
        bot.reply_to(message, f"📈 **{symbol}** : `{prix:.2f}`", parse_mode="Markdown")
    except IndexError:
        bot.reply_to(message, "⚠️ Précise un symbole. Exemple : `/prix AAPL` ou `/prix NVDA`.")
    except Exception:
        bot.reply_to(message, "⚠️ Erreur lors de la recherche du cours.")

# 3. Lancement du serveur et du bot
if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    bot.infinity_polling()
