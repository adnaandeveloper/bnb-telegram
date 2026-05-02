import os
import requests
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

DEX_API_PROFILES = "https://api.dexscreener.com/token-profiles/latest/v1"
DEX_API_BOOSTS = "https://api.dexscreener.com/token-boosts/latest/v1"

def fetch_bnb_tokens():
    tokens = []
    try:
        # 1. Hent seneste profiler
        r = requests.get(DEX_API_PROFILES, timeout=10)
        if r.status_code == 200:
            data = r.json()
            for t in data:
                if t.get("chainId") == "bsc":
                    tokens.append({
                        "name": t.get("description") or t.get("tokenName") or "Unknown",
                        "symbol": t.get("symbol") or t.get("tokenSymbol") or "",
                        "address": t.get("tokenAddress"),
                        "url": t.get("url")
                    })
        # 2. Hent boosts (giver flere BNB tokens)
        r2 = requests.get(DEX_API_BOOSTS, timeout=10)
        if r2.status_code == 200:
            for t in r2.json():
                if t.get("chainId") == "bsc":
                    tokens.append({
                        "name": t.get("description") or "Boosted",
                        "symbol": t.get("symbol") or "",
                        "address": t.get("tokenAddress"),
                        "url": t.get("url")
                    })
    except Exception as e:
        print("API fejl:", e)
    
    # Fjern dubletter
    seen = set()
    unique = []
    for t in tokens:
        addr = t["address"]
        if addr and addr not in seen:
            seen.add(addr)
            unique.append(t)
    return unique[:50]  # begræns til 50 for Telegram

def format_tokens(tokens):
    lines = []
    for t in tokens:
        name = t["name"][:30]
        symbol = t["symbol"]
        addr = t["address"]
        # Telegram markdown – kodeblok gør det kopierbart
        lines.append(f"*{name}* (${symbol})\n`{addr}`\n[Dexscreener]({t['url'] or f'https://dexscreener.com/bsc/{addr}'})\n")
    return "\n".join(lines)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hej! Jeg henter BNB Chain tokens fra Dexscreener.\nBrug /tokens for at se listen."
    )

async def tokens_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Henter BNB tokens... et øjeblik.")
    tokens = await asyncio.to_thread(fetch_bnb_tokens)
    if not tokens:
        await update.message.reply_text("Ingen data lige nu. Prøv igen.")
        return
    
    msg = format_tokens(tokens)
    # Telegram max 4096 tegn – split
    for i in range(0, len(msg), 3500):
        await update.message.reply_text(
            msg[i:i+3500],
            parse_mode="Markdown",
            disable_web_page_preview=True
        )

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("tokens", tokens_cmd))
    print("Bot kører...")
    app.run_polling()

if __name__ == "__main__":
    main()
