import os
import json
import asyncio
import random
import logging
import threading
from datetime import datetime
from flask import Flask, jsonify
from aiohttp import ClientSession, ClientTimeout
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, ConversationHandler
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
        "ping_interval": f"{PING_INTERVAL} seconds"
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
            json.dump(all_data, f)
    except Exception as e:
        logger.error(f"Failed to save URLs: {e}")

def get_all_urls():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.71 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.54 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.71 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.51 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.60 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.41 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.5005.61 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.5060.53 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.5112.79 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.5195.52 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.5249.61 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.5304.87 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.5359.71 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.5414.74 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.5481.77 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.2 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.3 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.4 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.5 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.6 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.71 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.54 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.71 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.51 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.60 Safari/537.36",
]

async def ping_url(url):
    try:
        params = {"_t": random.randint(100000, 999999)} if random.choice([True, False]) else {}
        headers = {"User-Agent": random.choice(USER_AGENTS)}
        timeout = ClientTimeout(total=10)
        async with ClientSession(timeout=timeout) as session:
            async with session.get(url, params=params, headers=headers) as resp:
                logger.info(f"Pinged {url} -> {resp.status}")
                return url, resp.status
    except Exception as e:
        logger.error(f"Failed to ping {url}: {e}")
        return url, None

def ping_all_sync():
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        all_urls = get_all_urls()
        if not all_urls:
            return
        
        all_tasks = []
        for user_id, urls in all_urls.items():
            for url in urls:
                all_tasks.append(ping_url(url))
        
        if all_tasks:
            loop.run_until_complete(asyncio.gather(*all_tasks))
        loop.close()
    except Exception as e:
        logger.error(f"Ping all error: {e}")

def scheduler_loop():
    while True:
        try:
            import time
            time.sleep(PING_INTERVAL)
            ping_all_sync()
        except Exception as e:
            logger.error(f"Scheduler error: {e}")
            import time
            time.sleep(5)

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

def start(update, context):
    try:
        user_id = update.effective_user.id
        context.user_data['user_id'] = user_id
        update.message.reply_text(
            f"🤖 WLZBI Render Free Tier Bypass Bot\n\n"
            f"Keep your Render free‑tier services alive by automatically pinging your URLs every {PING_INTERVAL} seconds.\n"
            f"Use the buttons below to manage your list.\n\n"
            f"{CREDIT}",
            reply_markup=main_menu_keyboard(),
        )
    except Exception as e:
        logger.error(f"Start error: {e}")

def menu_callback(update, context):
    try:
        query = update.callback_query
        query.answer()
        data = query.data
        user_id = update.effective_user.id

        if data == "menu":
            query.edit_message_text(
                f"🤖 WLZBI Render Free Tier Bypass Bot\n\n"
                f"Keep your Render free‑tier services alive by automatically pinging your URLs every {PING_INTERVAL} seconds.\n"
                f"Use the buttons below to manage your list.\n\n"
                f"{CREDIT}",
                reply_markup=main_menu_keyboard(),
            )
            return

        elif data == "add":
            query.edit_message_text(
                "📝 Please send me the URL you want to add.\n"
                "You can include http:// or https:// – I'll add it if missing.\n\n"
                "Type /cancel to abort.",
            )
            return WAITING_FOR_URL

        elif data == "remove":
            urls = load_urls(user_id)
            if not urls:
                query.edit_message_text(
                    "📭 No URLs stored.\n\n"
                    "Press Back to return.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="menu")]]),
                )
                return
            query.edit_message_text(
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
            
            query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="menu")]]),
            )
            return

        elif data == "clear":
            query.edit_message_text(
                "⚠️ Are you sure you want to delete ALL your URLs?\n"
                "This action cannot be undone.",
                reply_markup=clear_confirmation_keyboard(),
            )
            return
    except Exception as e:
        logger.error(f"Menu callback error: {e}")

def remove_callback(update, context):
    try:
        query = update.callback_query
        query.answer()
        data = query.data
        user_id = update.effective_user.id
        
        if data.startswith("remove_"):
            idx = int(data.split("_")[1])
            urls = load_urls(user_id)
            if 0 <= idx < len(urls):
                removed = urls.pop(idx)
                save_urls(user_id, urls)
                query.edit_message_text(
                    f"✅ Removed: {removed}",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="menu")]]),
                )
            else:
                query.edit_message_text(
                    "❌ Index out of range.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="menu")]]),
                )
    except Exception as e:
        logger.error(f"Remove callback error: {e}")

def clear_callback(update, context):
    try:
        query = update.callback_query
        query.answer()
        data = query.data
        user_id = update.effective_user.id
        
        if data == "clear_yes":
            save_urls(user_id, [])
            query.edit_message_text(
                "🗑 All your URLs have been cleared.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="menu")]]),
            )
        elif data == "clear_no":
            query.edit_message_text(
                "Action cancelled.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="menu")]]),
            )
    except Exception as e:
        logger.error(f"Clear callback error: {e}")

def add_url_message(update, context):
    try:
        user_id = update.effective_user.id
        url = update.message.text.strip()
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        
        urls = load_urls(user_id)
        if url in urls:
            update.message.reply_text(
                "⚠️ URL already exists.\n\n"
                "Press /start to return to the menu."
            )
        else:
            urls.append(url)
            save_urls(user_id, urls)
            update.message.reply_text(
                f"✅ Added: {url}\n\n"
                "Press /start to return to the menu.",
            )
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Add URL error: {e}")
        return ConversationHandler.END

def cancel(update, context):
    try:
        update.message.reply_text(
            "❌ Operation cancelled.\n\n"
            "Press /start to return to the menu."
        )
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Cancel error: {e}")
        return ConversationHandler.END

def fallback(update, context):
    try:
        update.message.reply_text(
            "❓ I don't understand that.\n"
            "Please use the buttons or type /start."
        )
    except Exception as e:
        logger.error(f"Fallback error: {e}")

def error_handler(update, context):
    logger.error(f"Update {update} caused error {context.error}")

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
        
        scheduler_thread = threading.Thread(target=scheduler_loop, daemon=True)
        scheduler_thread.start()
        
        updater = Updater(TOKEN, use_context=True)
        dp = updater.dispatcher

        conv_handler = ConversationHandler(
            entry_points=[CallbackQueryHandler(menu_callback, pattern="^add$")],
            states={
                WAITING_FOR_URL: [MessageHandler(Filters.text & ~Filters.command, add_url_message)],
            },
            fallbacks=[CommandHandler("cancel", cancel)],
        )
        dp.add_handler(conv_handler)

        dp.add_handler(CallbackQueryHandler(menu_callback, pattern="^(menu|list|clear)$"))
        dp.add_handler(CallbackQueryHandler(menu_callback, pattern="^remove$"))
        dp.add_handler(CallbackQueryHandler(remove_callback, pattern="^remove_"))
        dp.add_handler(CallbackQueryHandler(clear_callback, pattern="^clear_(yes|no)$"))

        dp.add_handler(CommandHandler("start", start))
        dp.add_handler(MessageHandler(Filters.text & ~Filters.command, fallback))
        dp.add_error_handler(error_handler)

        updater.start_polling()
        updater.idle()
    except Exception as e:
        logger.error(f"Main error: {e}")

if __name__ == "__main__":
    main()
