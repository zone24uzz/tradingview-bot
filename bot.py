import asyncio
import os
import logging
from typing import Dict, Any

from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from telegram.constants import ParseMode

from tradingview_server import get_indicators
from keep_alive import keep_alive

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

user_data_store = {}

LANGUAGES = {
    "uz": {
        "welcome": "Xush kelibsiz! Tilni tanlang / Выберите язык / Choose language:",
        "main_menu": "🎛 Asosiy menyu. Nimani tahlil qilamiz?",
        "crypto": "🪙 Kriptovalyuta",
        "forex": "💵 Valyuta (Forex)",
        "stocks": "📊 Aksiyalar",
        "futures": "📉 Fyuchers",
        "change_lang": "🌐 Tilni o'zgartirish",
        "select_asset": "Kategoriyani tanladingiz. Qaysi aktivni ko'rmoqchisiz?",
        "thinking": "⏳ O'ylayapman... Ma'lumotlar yuklanmoqda...",
        "analysis_result": "📊 <b>{symbol} tahlili:</b>\n\n💲 Narx: <code>{price}</code>\n\n📉 <b>Indikatorlar:</b>\n{indicators}",
        "error": "❌ Ma'lumot olishda xatolik yuz berdi.",
        "start_monitor": "🔔 Kuzatishni boshlash",
        "stop_monitor": "🔕 Kuzatishni to'xtatish",
        "monitor_started": "✅ {symbol} ni har {interval} soniyada kuzatishni boshladim. O'zgarish bo'lsa xabar beraman!",
        "monitor_stopped": "⛔️ {symbol} ni kuzatish to'xtatildi.",
        "market_change": "🔔 <b>Bozor o'zgarishi: {symbol}</b>\n💲 Yangi narx: <code>{price}</code>\n\n{changes}",
        "help_text": "🤖 <b>Bot qanday ishlaydi?</b>\n\n1️⃣ Asosiy menyudan o'zingizga kerakli bo'limni tanlang.\n2️⃣ Istalgan aktivni tanlab uning indikatorlarini ko'ring.\n3️⃣ <b>🔔 Kuzatishni boshlash</b> tugmasi orqali narxlarni avtomatik nazorat qiling (har 1 soniyada)!\n💡 Siz <b>bir vaqtning o'zida bir nechta aktivni</b> kuzatishingiz mumkin!\n\n/menu - Asosiy menyu\n/monitors - Faol kuzatuvlarni ko'rish\n/stop - Barcha kuzatuvlarni to'xtatish\n/help - Yordam",
        "stop_all": "🛑 Barcha kuzatuvlar (monitoring) muvaffaqiyatli to'xtatildi.",
        "active_monitors": "👀 Faol kuzatuvlar ({count})",
        "no_monitors": "🤷‍♂️ Sizda hozircha faol kuzatuvlar yo'q.",
        "monitors_list": "Siz quyidagi aktivlarni bir vaqtda kuzatyapsiz:\n\n{list}\n\nUlarni to'xtatish uchun /stop bosing."
    },
    "ru": {
        "welcome": "Добро пожаловать! Выберите язык:",
        "main_menu": "🎛 Главное меню. Что будем анализировать?",
        "crypto": "🪙 Криптовалюта",
        "forex": "💵 Валюта (Форекс)",
        "stocks": "📊 Акции",
        "futures": "📉 Фьючерсы",
        "change_lang": "🌐 Сменить язык",
        "select_asset": "Выберите актив для анализа:",
        "thinking": "⏳ Думаю... Загружаю данные рынка...",
        "analysis_result": "📊 <b>Анализ {symbol}:</b>\n\n💲 Цена: <code>{price}</code>\n\n📉 <b>Индикаторы:</b>\n{indicators}",
        "error": "❌ Ошибка при получении данных.",
        "start_monitor": "🔔 Начать отслеживание",
        "stop_monitor": "🔕 Остановить отслеживание",
        "monitor_started": "✅ Начал отслеживать {symbol} каждые {interval} сек. Сообщу при изменениях!",
        "monitor_stopped": "⛔️ Отслеживание {symbol} остановлено.",
        "market_change": "🔔 <b>Изменение рынка: {symbol}</b>\n💲 Новая цена: <code>{price}</code>\n\n{changes}",
        "help_text": "🤖 <b>Как работает бот?</b>\n\n1️⃣ Выберите нужный раздел из меню.\n2️⃣ Выберите актив и посмотрите его индикаторы.\n3️⃣ Нажмите <b>🔔 Начать отслеживание</b> для автоматического контроля (каждые 5 сек)!\n💡 Вы можете отслеживать несколько активов одновременно!\n\n/menu - Главное меню\n/monitors - Активные мониторинги\n/stop - Остановить все мониторинги\n/help - Помощь",
        "stop_all": "🛑 Все активные мониторинги остановлены.",
        "active_monitors": "👀 Активные мониторинги ({count})",
        "no_monitors": "🤷‍♂️ У вас пока нет активных мониторингов.",
        "monitors_list": "Вы одновременно отслеживаете:\n\n{list}\n\nНажмите /stop чтобы остановить."
    }
}

ASSETS = {
    "crypto": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT"],
    "forex": ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD"],
    "stocks": ["AAPL", "TSLA", "MSFT", "GOOGL", "AMZN", "NVDA"],
    "futures": ["SPY", "QQQ", "GLD", "USO"]  # Futures o'rniga ularning ETF lari ishlatiladi (ko'proq barqaror)
}

EXCHANGES = {
    # Crypto
    "BTCUSDT": "BINANCE", "ETHUSDT": "BINANCE", "SOLUSDT": "BINANCE", 
    "BNBUSDT": "BINANCE", "XRPUSDT": "BINANCE", "ADAUSDT": "BINANCE",
    # Forex
    "EURUSD": "FX_IDC", "GBPUSD": "FX_IDC", "USDJPY": "FX_IDC", 
    "AUDUSD": "FX_IDC", "USDCAD": "FX_IDC",
    # Stocks
    "AAPL": "NASDAQ", "TSLA": "NASDAQ", "MSFT": "NASDAQ", 
    "GOOGL": "NASDAQ", "AMZN": "NASDAQ", "NVDA": "NASDAQ",
    # Futures (ETFs)
    "SPY": "AMEX", "QQQ": "NASDAQ", "GLD": "AMEX", "USO": "AMEX"
}

def get_text(chat_id: int, key: str, **kwargs) -> str:
    lang = user_data_store.get(chat_id, {}).get("lang", "uz")
    text = LANGUAGES.get(lang, LANGUAGES["uz"]).get(key, key)
    if kwargs:
        return text.format(**kwargs)
    return text

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in user_data_store:
        user_data_store[chat_id] = {"lang": "uz", "monitoring": {}}
        
    keyboard = [
        [
            InlineKeyboardButton("🇺🇿 O'zbekcha", callback_data="lang_uz"),
            InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    user_name = update.effective_user.first_name
    welcome_text = (
        f"👋 Salom, <b>{user_name}</b>! TradingView tahlil botiga xush kelibsiz.\n"
        f"📈 Bu yerda siz valyutalar narxini va indikatorlarni real vaqtda kuzatib borishingiz mumkin.\n\n"
        f"🇺🇿 Iltimos, ishlash uchun tilni tanlang:\n\n"
        f"👋 Привет, <b>{user_name}</b>! Добро пожаловать в бота аналитики TradingView.\n"
        f"📈 Здесь вы можете отслеживать цены и индикаторы в реальном времени.\n\n"
        f"🇷🇺 Пожалуйста, выберите язык:"
    )
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

async def cmd_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in user_data_store:
        user_data_store[chat_id] = {"lang": "uz", "monitoring": {}}
    
    keyboard = [
        [InlineKeyboardButton(get_text(chat_id, "crypto"), callback_data="cat_crypto")],
        [InlineKeyboardButton(get_text(chat_id, "forex"), callback_data="cat_forex")],
        [InlineKeyboardButton(get_text(chat_id, "stocks"), callback_data="cat_stocks")],
        [InlineKeyboardButton(get_text(chat_id, "futures"), callback_data="cat_futures")],
        [InlineKeyboardButton(get_text(chat_id, "change_lang"), callback_data="change_lang")]
    ]
    text = get_text(chat_id, "main_menu")
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in user_data_store:
        user_data_store[chat_id] = {"lang": "uz", "monitoring": {}}
    text = get_text(chat_id, "help_text")
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

async def cmd_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in user_data_store:
        user_data_store[chat_id] = {"lang": "uz", "monitoring": {}}
    else:
        user_data_store[chat_id]["monitoring"] = {}  # Clear all monitors
        
    text = get_text(chat_id, "stop_all")
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

async def cmd_monitors(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in user_data_store:
        user_data_store[chat_id] = {"lang": "uz", "monitoring": {}}
        
    monitors = user_data_store[chat_id]["monitoring"]
    if not monitors:
        text = get_text(chat_id, "no_monitors")
        await update.message.reply_text(text)
        return
        
    symbols = list(monitors.keys())
    list_str = "\n".join([f"• <b>{sym}</b>" for sym in symbols])
    text = get_text(chat_id, "monitors_list", list=list_str)
    
    keyboard = [[InlineKeyboardButton(get_text(chat_id, "change_lang").split()[0] + " 🛑 Stop", callback_data="stop_all_monitors")]]
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = update.effective_chat.id
    
    monitoring_count = len(user_data_store.get(chat_id, {}).get("monitoring", {}))
    
    keyboard = [
        [InlineKeyboardButton(get_text(chat_id, "crypto"), callback_data="cat_crypto")],
        [InlineKeyboardButton(get_text(chat_id, "forex"), callback_data="cat_forex")],
        [InlineKeyboardButton(get_text(chat_id, "stocks"), callback_data="cat_stocks")],
        [InlineKeyboardButton(get_text(chat_id, "futures"), callback_data="cat_futures")]
    ]
    
    if monitoring_count > 0:
        btn_text = get_text(chat_id, "active_monitors", count=monitoring_count)
        keyboard.append([InlineKeyboardButton(btn_text, callback_data="view_monitors")])
        
    keyboard.append([InlineKeyboardButton(get_text(chat_id, "change_lang"), callback_data="change_lang")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = get_text(chat_id, "main_menu")
    if query:
        try:
            await query.message.edit_reply_markup(reply_markup=None)
        except:
            pass
        await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    chat_id = update.effective_chat.id
    
    if chat_id not in user_data_store:
        user_data_store[chat_id] = {"lang": "uz", "monitoring": {}}
    
    if data.startswith("lang_"):
        lang = data.split("_")[1]
        user_data_store[chat_id]["lang"] = lang
        await show_main_menu(update, context)
        
    elif data == "change_lang":
        keyboard = [
            [
                InlineKeyboardButton("🇺🇿 O'zbekcha", callback_data="lang_uz"),
                InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru")
            ]
        ]
        try:
            await query.message.edit_reply_markup(reply_markup=None)
        except:
            pass
        await context.bot.send_message(chat_id=chat_id, text="Tilni tanlang / Выберите язык:", reply_markup=InlineKeyboardMarkup(keyboard))
        
    elif data == "view_monitors":
        await cmd_monitors(update, context)
        
    elif data == "stop_all_monitors":
        user_data_store[chat_id]["monitoring"] = {}
        await query.message.edit_text(get_text(chat_id, "stop_all"))
        await show_main_menu(update, context)
        
    elif data.startswith("cat_"):
        category = data.split("_")[1]
        symbols = ASSETS.get(category, [])
        
        # Tugmalarni 2 ta qator qilib teramiz
        keyboard = []
        row = []
        for sym in symbols:
            row.append(InlineKeyboardButton(sym, callback_data=f"analyze_{sym}"))
            if len(row) == 2:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
            
        keyboard.append([InlineKeyboardButton("🔙 Orqaga / Назад", callback_data="back_main")])
        
        try:
            await query.message.edit_reply_markup(reply_markup=None)
        except:
            pass
        await context.bot.send_message(
            chat_id=chat_id,
            text=get_text(chat_id, "select_asset"), 
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    elif data == "back_main":
        await show_main_menu(update, context)
        
    elif data.startswith("analyze_"):
        symbol = data.split("_")[1]
        
        thinking_text = get_text(chat_id, "thinking")
        try:
            await query.message.edit_reply_markup(reply_markup=None)
        except:
            pass
        thinking_msg = await context.bot.send_message(chat_id=chat_id, text=thinking_text)
        
        # Exchange ni aniqlaymiz
        exchange = EXCHANGES.get(symbol, "BINANCE" if "USDT" in symbol else "")
        
        result = await get_indicators(symbol=symbol, exchange=exchange, timeframe="1m")
        
        if result.get("success"):
            indicators = result.get("indicators", {}).get("data", {})
            price = indicators.get("close", "N/A")
            rsi = indicators.get("RSI", "N/A")
            macd = indicators.get("MACD.macd", "N/A")
            recommendation = indicators.get("Recommend.All", "N/A")
            
            inds_text = f"• RSI: <code>{rsi}</code>\n• MACD: <code>{macd}</code>\n• Tavsiya: <b>{recommendation}</b>"
            
            final_text = get_text(chat_id, "analysis_result", symbol=symbol, price=price, indicators=inds_text)
            
            is_monitoring = symbol in user_data_store.get(chat_id, {}).get("monitoring", {})
            monitor_btn_text = get_text(chat_id, "stop_monitor" if is_monitoring else "start_monitor")
            monitor_cb = f"unmonitor_{symbol}" if is_monitoring else f"monitor_{symbol}"
            
            keyboard = [
                [InlineKeyboardButton(monitor_btn_text, callback_data=monitor_cb)],
                [InlineKeyboardButton("🔙 Orqaga / Назад", callback_data="back_main")]
            ]
            
            await thinking_msg.edit_text(final_text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            keyboard = [[InlineKeyboardButton("🔙 Orqaga / Назад", callback_data="back_main")]]
            await thinking_msg.edit_text(get_text(chat_id, "error") + f"\n\n{result.get('error')}", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("monitor_"):
        symbol = data.split("_")[1]
        user_data_store[chat_id]["monitoring"][symbol] = {}
        
        text = get_text(chat_id, "monitor_started", symbol=symbol, interval=5)
        # Yangi habar qilib jo'natamiz
        await context.bot.send_message(chat_id=chat_id, text=text)
        
        keyboard = [
            [InlineKeyboardButton(get_text(chat_id, "stop_monitor"), callback_data=f"unmonitor_{symbol}")],
            [InlineKeyboardButton("🔙 Orqaga / Назад", callback_data="back_main")]
        ]
        await query.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("unmonitor_"):
        symbol = data.split("_")[1]
        if symbol in user_data_store[chat_id]["monitoring"]:
            del user_data_store[chat_id]["monitoring"][symbol]
            
        text = get_text(chat_id, "monitor_stopped", symbol=symbol)
        await context.bot.send_message(chat_id=chat_id, text=text)
        
        keyboard = [
            [InlineKeyboardButton(get_text(chat_id, "start_monitor"), callback_data=f"monitor_{symbol}")],
            [InlineKeyboardButton("🔙 Orqaga / Назад", callback_data="back_main")]
        ]
        await query.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(keyboard))


async def handle_custom_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    symbol = update.message.text.upper().strip()
    chat_id = update.effective_chat.id
    
    if chat_id not in user_data_store:
        user_data_store[chat_id] = {"lang": "uz", "monitoring": {}}
        
    thinking_text = get_text(chat_id, "thinking")
    thinking_msg = await update.message.reply_text(thinking_text)
    
    exchange = EXCHANGES.get(symbol, "BINANCE" if "USDT" in symbol else "")
    result = await get_indicators(symbol=symbol, exchange=exchange, timeframe="1m")
    
    if result.get("success"):
        indicators = result.get("indicators", {}).get("data", {})
        price = indicators.get("close", "N/A")
        rsi = indicators.get("RSI", "N/A")
        macd = indicators.get("MACD.macd", "N/A")
        recommendation = indicators.get("Recommend.All", "N/A")
        
        inds_text = f"• RSI: <code>{rsi}</code>\n• MACD: <code>{macd}</code>\n• Tavsiya: <b>{recommendation}</b>"
        
        final_text = get_text(chat_id, "analysis_result", symbol=symbol, price=price, indicators=inds_text)
        
        is_monitoring = symbol in user_data_store.get(chat_id, {}).get("monitoring", {})
        monitor_btn_text = get_text(chat_id, "stop_monitor" if is_monitoring else "start_monitor")
        monitor_cb = f"unmonitor_{symbol}" if is_monitoring else f"monitor_{symbol}"
        
        keyboard = [
            [InlineKeyboardButton(monitor_btn_text, callback_data=monitor_cb)],
            [InlineKeyboardButton("🔙 Bosh menyu / Главное меню", callback_data="back_main")]
        ]
        
        await thinking_msg.edit_text(final_text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        keyboard = [[InlineKeyboardButton("🔙 Bosh menyu / Главное меню", callback_data="back_main")]]
        await thinking_msg.edit_text(get_text(chat_id, "error") + f"\n\nBunday aktiv topilmadi.", reply_markup=InlineKeyboardMarkup(keyboard))


async def background_monitor(context: ContextTypes.DEFAULT_TYPE):
    for chat_id, data in list(user_data_store.items()):
        monitoring = data.get("monitoring", {})
        for symbol, prev_state in list(monitoring.items()):
            try:
                exchange = EXCHANGES.get(symbol, "BINANCE" if "USDT" in symbol else "")
                result = await get_indicators(symbol=symbol, exchange=exchange, timeframe="1m")
                
                if result.get("success"):
                    indicators = result.get("indicators", {}).get("data", {})
                    current_price = str(indicators.get("close", "N/A"))
                    
                    changes = []
                    keys_to_track = ["close", "RSI", "Recommend.All"]
                    
                    if prev_state:
                        for key in keys_to_track:
                            new_val = str(indicators.get(key, ""))
                            old_val = str(prev_state.get(key, ""))
                            
                            if old_val and new_val and old_val != new_val:
                                changes.append(f"🔹 {key}: <code>{old_val}</code> ➡️ <code>{new_val}</code>")
                    
                    user_data_store[chat_id]["monitoring"][symbol] = {k: indicators.get(k) for k in keys_to_track}
                    
                    if changes:
                        changes_text = "\n".join(changes)
                        msg_text = get_text(chat_id, "market_change", symbol=symbol, price=current_price, changes=changes_text)
                        await context.bot.send_message(chat_id=chat_id, text=msg_text, parse_mode=ParseMode.HTML)
            
            except Exception as e:
                logger.error(f"Monitoring error for {symbol}: {e}")

def main():
    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_TOKEN topilmadi!")
        return
        
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", cmd_menu))
    application.add_handler(CommandHandler("help", cmd_help))
    application.add_handler(CommandHandler("stop", cmd_stop))
    application.add_handler(CommandHandler("monitors", cmd_monitors))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_custom_text))
    
    # Start the keep-alive server
    keep_alive()

    # Start the bot
    print("Starting bot...")
    
    # Background job (har 1 soniyada ishlashi uchun)
    job_queue = application.job_queue
    job_queue.run_repeating(background_monitor, interval=1, first=1)

    logger.info("Bot interaktiv rejimda ishga tushdi!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
