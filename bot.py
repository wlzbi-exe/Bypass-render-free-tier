import os
import json
import asyncio
import random
import logging
import threading
from datetime import datetime
from flask import Flask, jsonify
from aiohttp import ClientSession, ClientTimeout, TCPConnector
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler, ContextTypes
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("No BOT_TOKEN found in environment variables")

PING_INTERVAL = 10
DATA_FILE = "urls.json"
CREDIT = "— @rejerks | WLZBI"
ADMIN_ID = 7282835498

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return jsonify({
        "bot": "WLZBI Render Free Tier Bypass Bot",
        "status": "running",
        "credit": CREDIT,
        "ping_interval": f"{PING_INTERVAL} seconds",
        "version": "latest"
    })

def load_urls(user_id=None):
    try:
        with open(DATA_FILE, "r") as f:
            all_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        all_data = {}
    
    if user_id is None:
        return all_data
    return all_data.get(str(user_id), [])

def save_urls(user_id, urls):
    try:
        with open(DATA_FILE, "r") as f:
            all_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        all_data = {}
    
    all_data[str(user_id)] = urls
    
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(all_data, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save URLs: {e}")

def get_all_urls():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:133.0) Gecko/20100101 Firefox/133.0",
    "Mozilla/5.0 (X11; Linux i686; rv:133.0) Gecko/20100101 Firefox/133.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:133.0) Gecko/20100101 Firefox/133.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
]

async def ping_url(session, url):
    try:
        params = {"_t": random.randint(100000, 999999)} if random.choice([True, False]) else {}
        headers = {"User-Agent": random.choice(USER_AGENTS)}
        async with session.get(url, params=params, headers=headers, timeout=10) as resp:
            logger.info(f"Pinged {url} -> {resp.status}")
            return url, resp.status
    except Exception as e:
        logger.error(f"Failed to ping {url}: {e}")
        return url, None

async def ping_all():
    try:
        all_urls = get_all_urls()
        if not all_urls:
            return []
        
        connector = TCPConnector(limit=100, limit_per_host=20)
        async with ClientSession(connector=connector) as session:
            tasks = []
            for user_id, urls in all_urls.items():
                for url in urls:
                    tasks.append(ping_url(session, url))
            
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                return results
        return []
    except Exception as e:
        logger.error(f"Ping all error: {e}")
        return []

def main_menu_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("➕ Add URL", callback_data="add"),
            InlineKeyboardButton("➖ Remove URL", callback_data="remove")
        ],
        [
            InlineKeyboardButton("📋 List URLs", callback_data="list"),
            InlineKeyboardButton("🗑 Clear All", callback_data="clear")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def build_remove_keyboard(urls):
    keyboard = []
    for i, url in enumerate(urls):
        display = url if len(url) <= 40 else url[:37] + "..."
        keyboard.append([InlineKeyboardButton(f"❌ Remove #{i} – {display}", callback_data=f"remove_{i}")])
    keyboard.append([InlineKeyboardButton("🔙 Back to menu", callback_data="menu")])
    return InlineKeyboardMarkup(keyboard)

def clear_confirmation_keyboard():
    keyboard = [
        [InlineKeyboardButton("✅ Yes, clear all", callback_data="clear_yes")],
        [InlineKeyboardButton("❌ No, cancel", callback_data="clear_no")],
        [InlineKeyboardButton("🔙 Back to menu", callback_data="menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

WAITING_FOR_URL = 1

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        context.user_data['user_id'] = user_id
        await update.message.reply_text(
            f"🤖 WLZBI Render Free Tier Bypass Bot\n\n"
            f"Keep your Render free‑tier services alive by automatically pinging your URLs every {PING_INTERVAL} seconds.\n"
            f"Use the buttons below to manage your list.\n\n"
            f"{CREDIT}",
            reply_markup=main_menu_keyboard(),
        )
    except Exception as e:
        logger.error(f"Start error: {e}")

async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        data = query.data
        user_id = update.effective_user.id

        if data == "menu":
            await query.edit_message_text(
                f"🤖 WLZBI Render Free Tier Bypass Bot\n\n"
                f"Keep your Render free‑tier services alive by automatically pinging your URLs every {PING_INTERVAL} seconds.\n"
                f"Use the buttons below to manage your list.\n\n"
                f"{CREDIT}",
                reply_markup=main_menu_keyboard(),
            )
            return

        elif data == "add":
            await query.edit_message_text(
                "📝 Please send me the URL you want to add.\n"
                "You can include http:// or https:// – I'll add it if missing.\n\n"
                "Type /cancel to abort.",
            )
            return WAITING_FOR_URL

        elif data == "remove":
            urls = load_urls(user_id)
            if not urls:
                await query.edit_message_text(
                    "📭 No URLs stored.\n\n"
                    "Press Back to return.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="menu")]]),
                )
                return
            await query.edit_message_text(
                "🗑 Choose a URL to remove:",
                reply_markup=build_remove_keyboard(urls),
            )
            return

        elif data == "list":
            if user_id == ADMIN_ID:
                all_urls = get_all_urls()
                if not all_urls:
                    text = "📭 No URLs stored by any user."
                else:
                    text = "📋 All Users URLs:\n\n"
                    for uid, urls in all_urls.items():
                        text += f"User {uid}:\n"
                        for i, url in enumerate(urls):
                            text += f"  {i}. {url}\n"
                        text += "\n"
            else:
                urls = load_urls(user_id)
                if not urls:
                    text = "📭 No URLs stored."
                else:
                    text = "📋 Stored URLs:\n\n" + "\n".join(f"{i}. {url}" for i, url in enumerate(urls))
            
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="menu")]]),
            )
            return

        elif data == "clear":
            await query.edit_message_text(
                "⚠️ Are you sure you want to delete ALL your URLs?\n"
                "This action cannot be undone.",
                reply_markup=clear_confirmation_keyboard(),
            )
            return
    except Exception as e:
        logger.error(f"Menu callback error: {e}")

async def remove_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        data = query.data
        user_id = update.effective_user.id
        
        if data.startswith("remove_"):
            idx = int(data.split("_")[1])
            urls = load_urls(user_id)
            if 0 <= idx < len(urls):
                removed = urls.pop(idx)
                save_urls(user_id, urls)
                await query.edit_message_text(
                    f"✅ Removed: {removed}",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="menu")]]),
                )
            else:
                await query.edit_message_text(
                    "❌ Index out of range.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="menu")]]),
                )
    except Exception as e:
        logger.error(f"Remove callback error: {e}")

async def clear_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        data = query.data
        user_id = update.effective_user.id
        
        if data == "clear_yes":
            save_urls(user_id, [])
            await query.edit_message_text(
                "🗑 All your URLs have been cleared.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="menu")]]),
            )
        elif data == "clear_no":
            await query.edit_message_text(
                "Action cancelled.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="menu")]]),
            )
    except Exception as e:
        logger.error(f"Clear callback error: {e}")

async def add_url_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        url = update.message.text.strip()
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        
        urls = load_urls(user_id)
        if url in urls:
            await update.message.reply_text(
                "⚠️ URL already exists.\n\n"
                "Press /start to return to the menu."
            )
        else:
            urls.append(url)
            save_urls(user_id, urls)
            await update.message.reply_text(
                f"✅ Added: {url}\n\n"
                "Press /start to return to the menu.",
            )
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Add URL error: {e}")
        return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.reply_text(
            "❌ Operation cancelled.\n\n"
            "Press /start to return to the menu."
        )
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Cancel error: {e}")
        return ConversationHandler.END

async def fallback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.reply_text(
            "❓ I don't understand that.\n"
            "Please use the buttons or type /start."
        )
    except Exception as e:
        logger.error(f"Fallback error: {e}")

async def scheduler_loop():
    while True:
        try:
            await asyncio.sleep(PING_INTERVAL)
            await ping_all()
        except Exception as e:
            logger.error(f"Scheduler error: {e}")
            await asyncio.sleep(5)

async def bot_main():
    try:
        application = Application.builder().token(TOKEN).build()

        conv_handler = ConversationHandler(
            entry_points=[CallbackQueryHandler(menu_callback, pattern="^add$")],
            states={
                WAITING_FOR_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_url_message)],
            },
            fallbacks=[CommandHandler("cancel", cancel)],
        )
        application.add_handler(conv_handler)

        application.add_handler(CallbackQueryHandler(menu_callback, pattern="^(menu|list|clear)$"))
        application.add_handler(CallbackQueryHandler(menu_callback, pattern="^remove$"))
        application.add_handler(CallbackQueryHandler(remove_callback, pattern="^remove_"))
        application.add_handler(CallbackQueryHandler(clear_callback, pattern="^clear_(yes|no)$"))

        application.add_handler(CommandHandler("start", start))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, fallback))

        asyncio.create_task(scheduler_loop())
        
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            pass
        finally:
            await application.updater.stop()
            await application.stop()
            await application.shutdown()
    except Exception as e:
        logger.error(f"Bot main error: {e}")

def run_flask():
    try:
        port = int(os.environ.get("PORT", 5000))
        flask_app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
    except Exception as e:
        logger.error(f"Flask error: {e}")

def main():
    try:
        flask_thread = threading.Thread(target=run_flask, daemon=True)
        flask_thread.start()
        
        try:
            asyncio.run(bot_main())
        except RuntimeError:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(bot_main())
    except Exception as e:
        logger.error(f"Main error: {e}")

if __name__ == "__main__":
    main()
