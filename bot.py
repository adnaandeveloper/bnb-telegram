import os
import requests
import asyncio
import json
import time
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from dotenv import load_dotenv

# Hent token fra Railway Variables
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")

# ===== TEST FILTER – sender alt fra i dag + i går =====
MIN_LIQUIDITY = 0        # ingen krav
MIN_VOLUME_24H = 0       # ingen krav
MAX_AGE_HOURS = 48       # 48 timer = i dag og i går
# =====================================================

SEEN_FILE = "seen_tokens.json"
seen = set(json.load(open(SEEN_FILE)) if os.path.exists(SEEN_FILE) else [])

def save_seen():
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen), f)

def fetch_new_bnb():
    url = "https://api.dexscreener.com/latest/dex/search?q=bsc"
    try:
        r = requests.get(url, timeout=15)
        pairs = r.json().get("pairs", [])
        now = time.time() * 1000
        hits = []
        for p in pairs:
            if p.get("chainId") != "bsc":
                continue
            base = p["baseToken"]
            addr = base["address"]
            if addr in seen:
                continue

            liq = p.get("liquidity", {}).get("usd", 0) or 0
            vol = p.get("volume", {}).get("h24", 0) or 0
            created = p.get("pairCreatedAt", 0)
            age_hours = (now - created) / 3600000 if created else 999

            if liq >= MIN_LIQUIDITY and vol >= MIN_VOLUME_24H and age_hours <= MAX_AGE_HOURS:
                hits.append({
                    "name": base.get("name"),
                    "symbol": base.get("symbol"),
                    "address": addr,
                    "url": p.get("url"),
                    "liq": int(liq),
                    "vol": int(vol),
                    "age": round(age_hours, 1)
                })
                seen.add(addr)
        if hits:
            save_seen()
        return hits
    except Exception as e:
        print("API fejl:", e)
        return []

async def monitor(app):
    await asyncio.sleep(5)
    print("Monitor startet – TEST MODE 48h")
    while True:
        hits = await asyncio.to_thread(fetch_new_bnb)
        for h in hits:
            msg = (f"🧪 **TEST – NY BNB**\n\n"
                   f"*{h['name']}* (${h['symbol']})\n"
                   f"`{h['address']}`\n\n"
                   f"💧 Liq: ${h['liq']:,}\n"
                   f"📊 Vol 24h: ${h['vol']:,}\n"
                   f"⏱ Alder: {h['age']}t\n"
                   f"[Dexscreener]({h['url']})")
            try:
                await app.bot.send_message(
                    chat_id=ADMIN_CHAT_ID,
                    text=msg,
                    parse_mode="Markdown",
                    disable_web_page_preview=True
                )
            except Exception as e:
                print("Send fejl:", e)
        await asyncio.sleep(60)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot er live i TEST mode (48 timer).")

async def id_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Dit chat ID: `{update.effective_chat.id}`", parse_mode="Markdown")

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("id", id_cmd))

    async def on_startup(app):
        asyncio.create_task(monitor(app))
    app.post_init = on_startup

    print("Bot kører 24/7...")
    app.run_polling()

if __name__ == "__main__":
    main()