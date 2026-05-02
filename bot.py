import os, requests, asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")

def get_test_coins():
    url = "https://api.dexscreener.com/latest/dex/search?q=bsc"
    r = requests.get(url, timeout=15)
    pairs = r.json().get("pairs", [])[:5]  # tag bare 5
    coins = []
    for p in pairs:
        if p.get("chainId") == "bsc":
            b = p["baseToken"]
            coins.append({
                "name": b.get("name"),
                "symbol": b.get("symbol"),
                "address": b.get("address"),
                "url": p.get("url")
            })
    return coins

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Tester – sender 5 coins nu...")
    coins = await asyncio.to_thread(get_test_coins)
    for c in coins:
        msg = f"🧪 TEST\n*{c['name']}* (${c['symbol']})\n`{c['address']}`\n[Link]({c['url']})"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=msg, parse_mode="Markdown")

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    print("Bot kører...")
    app.run_polling()

if __name__ == "__main__":
    main()