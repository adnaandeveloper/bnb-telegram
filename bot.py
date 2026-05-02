import os
import requests
import asyncio
import json
import time
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ===== RAILWAY VARIABLES =====
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")

if not TOKEN:
    raise RuntimeError("❌ TELEGRAM_BOT_TOKEN mangler i Railway Variables!")
if not ADMIN_CHAT_ID:
    raise RuntimeError("❌ ADMIN_CHAT_ID mangler i Railway Variables!")

print(f"Token loaded: {TOKEN[:10]}... Chat ID: {ADMIN_CHAT_ID}")
# =============================

# ===== BALANCERET FILTER =====
MIN_AGE_MIN = 5
MAX_AGE_HOURS = 3
MIN_LIQ = 8000
MAX_LIQ = 150000
MIN_VOL_24H = 3000
MIN_BUYS_H1 = 10
BUY_SELL_RATIO = 1.3
MAX_PRICECHANGE_H1 = 200
MAX_FDV = 500000
# =============================

SEEN_FILE = "seen_tokens.json"
seen = set(json.load(open(SEEN_FILE)) if os.path.exists(SEEN_FILE) else [])

def save_seen():
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen), f)

def goplus_check(address):
    try:
        url = f"https://api.gopluslabs.io/api/v1/token_security/56?contract_addresses={address}"
        r = requests.get(url, timeout=10).json()
        data = r.get("result", {}).get(address.lower(), {})
        if data.get("is_honeypot") == "1": return False, "Honeypot"
        if data.get("is_mintable") == "1": return False, "Mintable"
        buy_tax = float(data.get("buy_tax", "0") or 0)
        sell_tax = float(data.get("sell_tax", "0") or 0)
        if buy_tax > 10 or sell_tax > 10: return False, f"High tax {buy_tax}/{sell_tax}%"
        if data.get("is_open_source")!= "1": return False, "Ikke verificeret"
        return True, "Safe"
    except:
        return True, "Check fejlede"

def fetch_new_bnb():
    try:
        profiles = requests.get("https://api.dexscreener.com/token-profiles/latest/v1", timeout=15).json()
        bnb = [p for p in profiles if p.get("chainId") == "bsc"][:30]
        hits = []
        now = time.time() * 1000

        for prof in bnb:
            addr = prof.get("tokenAddress")
            if not addr or addr in seen: continue

            pair_data = requests.get(f"https://api.dexscreener.com/latest/dex/tokens/{addr}", timeout=10).json()
            pairs = pair_data.get("pairs", [])
            if not pairs: continue
            p = pairs[0]

            created = p.get("pairCreatedAt", 0)
            age_hours = (now - created) / 3600000 if created else 999
            if not (MIN_AGE_MIN/60 <= age_hours <= MAX_AGE_HOURS): continue

            liq = p.get("liquidity", {}).get("usd", 0) or 0
            if not (MIN_LIQ <= liq <= MAX_LIQ): continue

            vol = p.get("volume", {}).get("h24", 0) or 0
            if vol < MIN_VOL_24H: continue

            txns = p.get("txns", {}).get("h1", {})
            buys = txns.get("buys", 0)
            sells = txns.get("sells", 1)
            if buys < MIN_BUYS_H1 or buys < sells * BUY_SELL_RATIO: continue

            price_chg = p.get("priceChange", {}).get("h1", 0) or 0
            if price_chg > MAX_PRICECHANGE_H1: continue

            fdv = p.get("fdv", 0) or 0
            if fdv > MAX_FDV: continue

            safe, reason = goplus_check(addr)
            if not safe: continue

            hits.append({
                "name": p["baseToken"]["name"],
                "symbol": p["baseToken"]["symbol"],
                "address": addr,
                "url": p.get("url"),
                "liq": int(liq),
                "vol": int(vol),
                "age_min": int(age_hours*60),
                "buys": buys,
                "sells": sells,
                "fdv": int(fdv)
            })
            seen.add(addr)

        if hits: save_seen()
        return hits
    except Exception as e:
        print("Fetch fejl:", e)
        return []

async def monitor(app):
    await asyncio.sleep(10)
    print("Monitor startet – BALANCERET mode")
    while True:
        hits = await asyncio.to_thread(fetch_new_bnb)
        for h in hits:
            msg = (f"🚨 **NY BNB – BALANCERET**\n\n"
                   f"*{h['name']}* (${h['symbol']})\n"
                   f"`{h['address']}`\n\n"
                   f"⏱ {h['age_min']} min | 💧 ${h['liq']:,} liq\n"
                   f"📊 ${h['vol']:,} vol | 💰 FDV ${h['fdv']:,}\n"
                   f"🟢 Buys {h['buys']} / Sells {h['sells']}\n"
                   f"✅ GoPlus Safe\n\n"
                   f"[Dexscreener]({h['url']}) | [PancakeSwap](https://pancakeswap.finance/swap?outputCurrency={h['address']})")
            try:
                await app.bot.send_message(chat_id=ADMIN_CHAT_ID, text=msg, parse_mode="Markdown", disable_web_page_preview=True)
            except Exception as e:
                print("Send fejl:", e)
        await asyncio.sleep(60)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot kører BALANCERET 24/7. Du får besked automatisk.")

async def id_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"ID: `{update.effective_chat.id}`", parse_mode="Markdown")

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("id", id_cmd))
    async def on_startup(app): asyncio.create_task(monitor(app))
    app.post_init = on_startup
    print("Bot kører...")
    app.run_polling()

if __name__ == "__main__":
    main()