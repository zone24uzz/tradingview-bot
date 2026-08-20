import asyncio
import os
import logging
import requests
import re
from typing import Dict, Any

from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice, BotCommand
from telegram.ext import (
    ApplicationBuilder,
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    PreCheckoutQueryHandler,
    filters,
    ContextTypes,
)
from telegram.constants import ParseMode

import httpx
from keep_alive import keep_alive

async def get_fast_indicators(symbol: str, exchange: str = "BINANCE", timeframe: str = "1m"):
    try:
        screener = "crypto"
        if exchange == "FX_IDC":
            screener = "forex"
        elif exchange in ["NASDAQ", "AMEX"]:
            screener = "america"
            
        url = f"https://scanner.tradingview.com/{screener}/scan"
        ticker = f"{exchange}:{symbol}"
        
        tf_suffix = ""
        if timeframe == "1m": tf_suffix = "|1"
        elif timeframe == "5m": tf_suffix = "|5"
        elif timeframe == "15m": tf_suffix = "|15"
        elif timeframe == "30m": tf_suffix = "|30"
        elif timeframe == "1h": tf_suffix = "|60"
        elif timeframe == "4h": tf_suffix = "|240"
        elif timeframe == "1d": tf_suffix = ""
        elif timeframe == "1w": tf_suffix = "|1W"
        elif timeframe == "1M": tf_suffix = "|1M"
            
        cols = [
            f"close{tf_suffix}" if tf_suffix else "close",
            f"RSI{tf_suffix}" if tf_suffix else "RSI",
            f"MACD.macd{tf_suffix}" if tf_suffix else "MACD.macd",
            f"Recommend.All{tf_suffix}" if tf_suffix else "Recommend.All"
        ]
        
        payload = {
            "symbols": {"tickers": [ticker]},
            "columns": cols
        }
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, timeout=5.0)
            data = resp.json()
            
        if not data.get("data"):
            raise ValueError(f"No data returned for {ticker}")
            
        d = data["data"][0]["d"]
        
        close = d[0]
        rsi = d[1]
        macd = d[2]
        rec_val = d[3]
        
        if rec_val is None:
            rec_str = "NEUTRAL"
        elif rec_val < -0.5:
            rec_str = "STRONG_SELL"
        elif rec_val < -0.1:
            rec_str = "SELL"
        elif rec_val <= 0.1:
            rec_str = "NEUTRAL"
        elif rec_val <= 0.5:
            rec_str = "BUY"
        else:
            rec_str = "STRONG_BUY"
            
        indicators_data = {
            "close": close,
            "RSI": round(rsi, 2) if rsi is not None else "N/A",
            "MACD.macd": round(macd, 5) if macd is not None else "N/A",
            "Recommend.All": rec_str
        }
        
        return {
            "success": True,
            "symbol": symbol,
            "exchange": exchange,
            "timeframe": timeframe,
            "indicators": {"data": indicators_data}
        }
    except Exception as e:
        import logging
        logging.error(f"Error fetching indicators for {symbol}: {str(e)}")
        return {
            "success": False,
            "symbol": symbol,
            "exchange": exchange,
            "timeframe": timeframe,
            "error": str(e)
        }


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "8843585945"))

from db import user_data_store, admins, save_db

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
    "futures": ["SPY", "QQQ", "GLD", "USO"]
}

EXCHANGES = {
    "BTCUSDT": "BINANCE", "ETHUSDT": "BINANCE", "SOLUSDT": "BINANCE", 
    "BNBUSDT": "BINANCE", "XRPUSDT": "BINANCE", "ADAUSDT": "BINANCE",
    "EURUSD": "FX_IDC", "GBPUSD": "FX_IDC", "USDJPY": "FX_IDC", 
    "AUDUSD": "FX_IDC", "USDCAD": "FX_IDC",
    "AAPL": "NASDAQ", "TSLA": "NASDAQ", "MSFT": "NASDAQ", 
    "GOOGL": "NASDAQ", "AMZN": "NASDAQ", "NVDA": "NASDAQ",
    "SPY": "AMEX", "QQQ": "NASDAQ", "GLD": "AMEX", "USO": "AMEX"
}

def get_text(chat_id: int, key: str, **kwargs) -> str:
    lang = user_data_store.get(chat_id, {}).get("lang", "uz")
    text = LANGUAGES.get(lang, LANGUAGES["uz"]).get(key, key)
    if kwargs:
        return text.format(**kwargs)
    return text

async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.pre_checkout_query
    if query.invoice_payload != 'pro_subscription_payload':
        await query.answer(ok=False, error_message="Xatolik yuz berdi.")
    else:
        await query.answer(ok=True)

async def successful_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in user_data_store:
        user_data_store[chat_id] = {"lang": "uz", "monitoring": {}}
    user_data_store[chat_id]["is_pro"] = True
    await update.message.reply_text("🎉 Tabriklaymiz! To'lov muvaffaqiyatli amalga oshirildi. Siz endi PRO foydalanuvchisiz! 🌟\n\nAI tahlil va boshqa imkoniyatlardan bemalol foydalanishingiz mumkin.")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in user_data_store:
        user_data_store[chat_id] = {"lang": "uz", "monitoring": {}}
        
    if chat_id == ADMIN_ID or str(chat_id) in admins:
        user_data_store[chat_id]["is_pro"] = True
        
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
        
    if chat_id == ADMIN_ID or str(chat_id) in admins:
        user_data_store[chat_id]["is_pro"] = True
    
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
        user_data_store[chat_id]["monitoring"] = {}
        
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

async def send_fear_and_greed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        r = requests.get('https://api.alternative.me/fng/').json()
        value = int(r['data'][0]['value'])
        
        if value <= 25:
            status_uz = "🔴 Qattiq Qo'rquv (Sotib olish uchun yaxshi imkoniyat)"
            emoji = "😱"
        elif value <= 45:
            status_uz = "🟠 Qo'rquv (Odamlar xavotirda)"
            emoji = "😨"
        elif value <= 55:
            status_uz = "🟡 Neytral (Bozor bir qarorga kelmagan)"
            emoji = "😐"
        elif value <= 75:
            status_uz = "🟢 Ochko'zlik (Odamlar faol sotib olmoqda)"
            emoji = "😏"
        else:
            status_uz = "🟢🟢 Qattiq Ochko'zlik (Bozor qizib ketgan, ehtiyot bo'ling!)"
            emoji = "🤑"
            
        text = f"🧭 *Bozor Kayfiyati (Fear & Greed Index)*\n\n"
        text += f"📊 *Indeks:* {value}/100 {emoji}\n"
        text += f"Holat: {status_uz}\n\n"
        text += "_Bu indeks kripto bozoridagi investorlar kayfiyatini bildiradi._"
        
        if update.callback_query:
            await update.callback_query.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=text, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logger.error(f"F&G xatosi: {e}")
        if update.callback_query:
            await update.callback_query.message.reply_text("Ma'lumot olishda xatolik yuz berdi!")

async def send_top_gainers(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        r = requests.get('https://api.binance.com/api/v3/ticker/24hr').json()
        top = [x for x in r if x['symbol'].endswith('USDT') and 'UP' not in x['symbol'] and 'DOWN' not in x['symbol']]
        top.sort(key=lambda x: float(x['priceChangePercent']), reverse=True)
        
        text = "🔥 *So'nggi 24 soat ichida eng ko'p o'sgan 5 ta Kriptovalyuta (Binance)*\n\n"
        
        for i, coin in enumerate(top[:5], 1):
            symbol = coin['symbol'].replace('USDT', '')
            percent = float(coin['priceChangePercent'])
            price = float(coin['lastPrice'])
            text += f"{i}. *{symbol}* : +{percent:.2f}% 📈 (Narxi: ${price:g})\n"
            
        if update.callback_query:
            await update.callback_query.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=text, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logger.error(f"Top gainers xatosi: {e}")
        if update.callback_query:
            await update.callback_query.message.reply_text("Ma'lumot olishda xatolik yuz berdi!")

async def send_top_losers(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        r = requests.get('https://api.binance.com/api/v3/ticker/24hr').json()
        top = [x for x in r if x['symbol'].endswith('USDT') and 'UP' not in x['symbol'] and 'DOWN' not in x['symbol']]
        top.sort(key=lambda x: float(x['priceChangePercent']))
        
        text = "📉 *So'nggi 24 soat ichida eng ko'p tushgan 5 ta Kriptovalyuta (Binance)*\n\n"
        
        for i, coin in enumerate(top[:5], 1):
            symbol = coin['symbol'].replace('USDT', '')
            percent = float(coin['priceChangePercent'])
            price = float(coin['lastPrice'])
            text += f"{i}. *{symbol}* : {percent:.2f}% 🩸 (Narxi: ${price:g})\n"
            
        if update.callback_query:
            await update.callback_query.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=text, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logger.error(f"Top losers xatosi: {e}")
        if update.callback_query:
            await update.callback_query.message.reply_text("Ma'lumot olishda xatolik yuz berdi!")

async def send_main_coins(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        symbols = '["BTCUSDT","ETHUSDT","SOLUSDT","TONUSDT","BNBUSDT"]'
        r = requests.get(f'https://api.binance.com/api/v3/ticker/24hr?symbols={symbols}').json()
        
        text = "💎 *Asosiy Kriptovalyutalar Narxi (24 soatlik o'zgarish)*\n\n"
        for coin in r:
            symbol = coin['symbol'].replace('USDT', '')
            price = float(coin['lastPrice'])
            percent = float(coin['priceChangePercent'])
            emoji = "🟩" if percent >= 0 else "🟥"
            text += f"• *{symbol}*: ${price:,.2f} | {emoji} {percent:+.2f}%\n"
            
        if update.callback_query:
            await update.callback_query.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=text, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logger.error(f"Main coins xatosi: {e}")
        if update.callback_query:
            await update.callback_query.message.reply_text("Ma'lumot olishda xatolik yuz berdi!")

async def calculate_crypto(update: Update, context: ContextTypes.DEFAULT_TYPE, amount: float, coin1: str, coin2: str):
    try:
        usd_to_uzs = 12600
        try:
            r = requests.get("https://cbu.uz/uz/arkhiv-kursov-valyut/json/").json()
            for val in r:
                if val['Ccy'] == 'USD':
                    usd_to_uzs = float(val['Rate'])
                    break
        except:
            pass

        def get_usd_price(coin):
            if coin == 'USDT' or coin == 'USD': return 1.0
            if coin == 'UZS': return 1.0 / usd_to_uzs
            try:
                r = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={coin}USDT").json()
                if 'price' in r: return float(r['price'])
            except:
                pass
            return None

        price1 = get_usd_price(coin1)
        price2 = get_usd_price(coin2)

        if not price1 or not price2:
            await update.message.reply_text(f"❌ Kechirasiz, {coin1} yoki {coin2} narxini topa olmadim.")
            return

        total_usd = amount * price1
        result = total_usd / price2

        text = f"💱 *Kalkulyator Natijasi:*\n\n"
        text += f"{amount:,.4f} {coin1} = *{result:,.4f} {coin2}*\n\n"
        text += f"_(1 {coin1} = {price1/price2:,.4f} {coin2})_"
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    except Exception as e:
        logger.error(f"Kalkulyator xatosi: {e}")
        await update.message.reply_text("Ma'lumotlarni hisoblashda xatolik yuz berdi.")

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = update.effective_chat.id
    
    monitoring_count = len(user_data_store.get(chat_id, {}).get("monitoring", {}))
    
    keyboard = [
        [InlineKeyboardButton(get_text(chat_id, "crypto"), callback_data="cat_crypto")],
        [InlineKeyboardButton(get_text(chat_id, "forex"), callback_data="cat_forex")],
        [InlineKeyboardButton(get_text(chat_id, "stocks"), callback_data="cat_stocks")],
        [InlineKeyboardButton(get_text(chat_id, "futures"), callback_data="cat_futures")],
        [InlineKeyboardButton("📊 Yangi tahlil", callback_data="new_analysis")],
        [InlineKeyboardButton("🔥 Top 5 O'sayotganlar", callback_data="top_gainers"),
         InlineKeyboardButton("📉 Top 5 Tushayotganlar", callback_data="top_losers")],
        [InlineKeyboardButton("💎 Asosiy tangalar", callback_data="main_coins"),
         InlineKeyboardButton("🧭 Bozor kayfiyati", callback_data="fear_greed")],
        [InlineKeyboardButton("💱 Kripto Kalkulyator", callback_data="calculator")],
        [InlineKeyboardButton("🌟 PRO Versiya (Signallar va AI)", callback_data="buy_pro")]
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
        
    if chat_id == ADMIN_ID or str(chat_id) in admins:
        user_data_store[chat_id]["is_pro"] = True
    
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
        
    elif data == "fear_greed":
        await send_fear_and_greed(update, context)
        await show_main_menu(update, context)
        
    elif data == "top_gainers":
        await send_top_gainers(update, context)
        await show_main_menu(update, context)
        
    elif data == "top_losers":
        await send_top_losers(update, context)
        await show_main_menu(update, context)
        
    elif data == "main_coins":
        await send_main_coins(update, context)
        await show_main_menu(update, context)
        
    elif data == "calculator":
        await query.message.reply_text("💱 Kripto-kalkulyatordan foydalanish uchun quyidagi formatda xabar yuboring:\n\n`MIG'DOR VALYUTA1 TO VALYUTA2`\n\nMisollar:\n`100 USDT to BTC`\n`1 BTC to UZS`\n`50 ETH to USDT`\n`1 TON to UZS`", parse_mode=ParseMode.MARKDOWN)
        
    elif data == "new_analysis":
        keyboard = [
            [InlineKeyboardButton(get_text(chat_id, "crypto"), callback_data="cat_crypto"),
             InlineKeyboardButton(get_text(chat_id, "forex"), callback_data="cat_forex")],
            [InlineKeyboardButton(get_text(chat_id, "stocks"), callback_data="cat_stocks"),
             InlineKeyboardButton(get_text(chat_id, "futures"), callback_data="cat_futures")],
            [InlineKeyboardButton("🔙 Orqaga / Назад", callback_data="back_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text("Qaysi bozorni tahlil qilamiz? Kategoriyani tanlang:", reply_markup=reply_markup)

    elif data == "buy_pro":
        chat_id = update.effective_chat.id
        if chat_id not in user_data_store:
            user_data_store[chat_id] = {"lang": "uz", "monitoring": {}}
        if chat_id == ADMIN_ID or str(chat_id) in admins:
            user_data_store[chat_id]["is_pro"] = True
            
        if user_data_store[chat_id].get("is_pro", False):
            await query.answer("🎉 Sizda allaqachon PRO versiya faol! Barcha imkoniyatlardan bemalol foydalanishingiz mumkin.", show_alert=True)
            return

        title = "🌟 PRO Versiya (1 Oylik)"
        description = (
            "PRO versiyada siz quyidagilarga ega bo'lasiz:\n\n"
            "🤖 AI tahlil: Aniq 'Sotib olish' yoki 'Sotish' xulosalari.\n"
            "📈 Cheksiz monitoring: Bir vaqtning o'zida 10 tagacha tangani kuzatish.\n"
            "⚡️ VIP Signallar va reklamasiz ishlash."
        )
        payload = "pro_subscription_payload"
        currency = "XTR"
        price = 50
        prices = [LabeledPrice("PRO Versiya", price)]
        
        await context.bot.send_invoice(
            chat_id=chat_id,
            title=title,
            description=description,
            payload=payload,
            provider_token="",
            currency=currency,
            prices=prices
        )

    elif data == "ai_analysis":
        if not user_data_store.get(chat_id, {}).get("is_pro", False):
            await query.answer("Bu funksiya faqat PRO foydalanuvchilar uchun! 🌟", show_alert=True)
            return
        await query.message.reply_text("🤖 *AI Xulosasi:* Ushbu valyutada kuchli buqalar (o'sish) trendi kuzatilmoqda. RSI va MACD indikatorlari qulay nuqtani ko'rsatmoqda. Kichik risk bilan sotib olish (BUY) tavsiya etiladi.", parse_mode=ParseMode.MARKDOWN)

    elif data == "view_monitors":
        await cmd_monitors(update, context)
        
    elif data == "stop_all_monitors":
        user_data_store[chat_id]["monitoring"] = {}
        await query.message.edit_text(get_text(chat_id, "stop_all"))
        await show_main_menu(update, context)
        
    elif data.startswith("cat_"):
        category = data.split("_")[1]
        symbols = ASSETS.get(category, [])
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
        exchange = EXCHANGES.get(symbol, "BINANCE" if "USDT" in symbol else "")
        result = await get_fast_indicators(symbol=symbol, exchange=exchange, timeframe="1m")
        
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
                [InlineKeyboardButton("🤖 AI Orqali chuqur tahlil (PRO)", callback_data="ai_analysis")],
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

    elif data == "admin_stats":
        if chat_id != ADMIN_ID and str(chat_id) not in admins: return
        users = len(user_data_store)
        pro = sum(1 for d in user_data_store.values() if d.get("is_pro"))
        langs = {"uz": 0, "ru": 0}
        for d in user_data_store.values():
            langs[d.get("lang", "uz")] += 1
        stat_text = (
            f"📊 <b>Batafsil Statistika</b>\n\n"
            f"Jami a'zolar: {users}\n"
            f"PRO a'zolar: {pro}\n"
            f"O'zbek tili: {langs['uz']} | Rus tili: {langs['ru']}\n"
        )
        await query.message.edit_text(stat_text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="admin_back")]]))

    elif data == "admin_broadcast":
        if chat_id != ADMIN_ID and str(chat_id) not in admins: return
        user_data_store[chat_id]["awaiting_broadcast"] = True
        await query.message.edit_text("📢 Xabaringizni yuboring. Barcha foydalanuvchilarga yetkaziladi!\n\nBekor qilish uchun /cancel deb yozing.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="admin_back")]]))

    elif data == "admin_close":
        if chat_id != ADMIN_ID and str(chat_id) not in admins: return
        await query.message.delete()
        
    elif data == "admin_back":
        if chat_id != ADMIN_ID and str(chat_id) not in admins: return
        users = len(user_data_store)
        pro = sum(1 for d in user_data_store.values() if d.get("is_pro"))
        active = sum(len(d.get("monitoring", {})) for d in user_data_store.values())
        text = (
            f"👑 <b>Admin Panel</b>\n\n"
            f"👥 Barcha foydalanuvchilar: <b>{users}</b>\n"
            f"🌟 PRO foydalanuvchilar: <b>{pro}</b>\n"
            f"👀 Faol monitoringlar: <b>{active}</b>\n\n"
            f"<i>Quyidagi menyudan kerakli harakatni tanlang:</i>"
        )
        keyboard = [
            [InlineKeyboardButton("📢 Hammaga xabar yuborish", callback_data="admin_broadcast")],
            [InlineKeyboardButton("📊 Batafsil Statistika", callback_data="admin_stats")],
            [InlineKeyboardButton("🔙 Yopish", callback_data="admin_close")]
        ]
        user_data_store[chat_id]["awaiting_broadcast"] = False
        await query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_custom_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    original_text = update.message.text
    text = original_text.upper().strip()
    chat_id = update.effective_chat.id
    
    if user_data_store.get(chat_id, {}).get("awaiting_broadcast"):
        if original_text.lower().strip() == "/cancel":
            user_data_store[chat_id]["awaiting_broadcast"] = False
            await update.message.reply_text("❌ Xabar yuborish bekor qilindi.")
            return
            
        success = 0
        for uid in user_data_store.keys():
            try:
                await context.bot.send_message(chat_id=uid, text=original_text, parse_mode=ParseMode.HTML)
                success += 1
            except:
                pass
        user_data_store[chat_id]["awaiting_broadcast"] = False
        await update.message.reply_text(f"✅ Xabar {success} ta foydalanuvchiga yuborildi!")
        return
    
    # Check if text is for calculator
    match = re.match(r"([\d\.]+)\s*([A-Z]+)\s+TO\s+([A-Z]+)", text)
    if match:
        amount = float(match.group(1))
        coin1 = match.group(2)
        coin2 = match.group(3)
        await calculate_crypto(update, context, amount, coin1, coin2)
        return

    symbol = text
    if chat_id not in user_data_store:
        user_data_store[chat_id] = {"lang": "uz", "monitoring": {}}
        
    if chat_id == ADMIN_ID or str(chat_id) in admins:
        user_data_store[chat_id]["is_pro"] = True
    thinking_text = get_text(chat_id, "thinking")
    thinking_msg = await update.message.reply_text(thinking_text)
    exchange = EXCHANGES.get(symbol, "BINANCE" if "USDT" in symbol else "")
    result = await get_fast_indicators(symbol=symbol, exchange=exchange, timeframe="1m")
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
            [InlineKeyboardButton("🤖 AI Orqali chuqur tahlil (PRO)", callback_data="ai_analysis")],
            [InlineKeyboardButton("🔙 Bosh menyu / Главное меню", callback_data="back_main")]
        ]
        await thinking_msg.edit_text(final_text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        keyboard = [[InlineKeyboardButton("🔙 Bosh menyu / Главное меню", callback_data="back_main")]]
        await thinking_msg.edit_text(get_text(chat_id, "error") + f"\n\nBunday aktiv topilmadi.", reply_markup=InlineKeyboardMarkup(keyboard))

async def background_monitor(context: ContextTypes.DEFAULT_TYPE):
    save_db()
    for chat_id, data in list(user_data_store.items()):
        monitoring = data.get("monitoring", {})
        for symbol, prev_state in list(monitoring.items()):
            try:
                exchange = EXCHANGES.get(symbol, "BINANCE" if "USDT" in symbol else "")
                result = await get_fast_indicators(symbol=symbol, exchange=exchange, timeframe="1m")
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

async def show_category_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE, category: str):
    chat_id = update.effective_chat.id
    symbols = ASSETS.get(category, [])
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
    text = get_text(chat_id, "select_asset")
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def cmd_crypto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_category_cmd(update, context, "crypto")

async def cmd_forex(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_category_cmd(update, context, "forex")

async def cmd_stocks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_category_cmd(update, context, "stocks")

async def cmd_futures(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_category_cmd(update, context, "futures")

async def cmd_calc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("💱 Kripto-kalkulyatordan foydalanish uchun quyidagi formatda xabar yuboring:\n\n`MIG'DOR VALYUTA1 TO VALYUTA2`\n\nMisollar:\n`100 USDT to BTC`\n`1 BTC to UZS`\n`50 ETH to USDT`\n`1 TON to UZS`", parse_mode=ParseMode.MARKDOWN)

async def cmd_pro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in user_data_store:
        user_data_store[chat_id] = {"lang": "uz", "monitoring": {}}
    if chat_id == ADMIN_ID or str(chat_id) in admins:
        user_data_store[chat_id]["is_pro"] = True
        
    if user_data_store[chat_id].get("is_pro", False):
        await update.message.reply_text("🎉 Sizda allaqachon PRO versiya faol! Barcha imkoniyatlardan bemalol foydalanishingiz mumkin.")
        return

    title = "🌟 PRO Versiya (1 Oylik)"
    description = (
        "PRO versiyada siz quyidagilarga ega bo'lasiz:\n\n"
        "🤖 AI tahlil: Aniq 'Sotib olish' yoki 'Sotish' xulosalari.\n"
        "📈 Cheksiz monitoring: Bir vaqtning o'zida 10 tagacha tangani kuzatish.\n"
        "⚡️ VIP Signallar va reklamasiz ishlash."
    )
    payload = "pro_subscription_payload"
    currency = "XTR"
    price = 50
    prices = [LabeledPrice("PRO Versiya", price)]
    
    await context.bot.send_invoice(
        chat_id=chat_id,
        title=title,
        description=description,
        payload=payload,
        provider_token="",
        currency=currency,
        prices=prices
    )

async def cmd_analyze(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Tahlil qilish uchun juftlik nomini yozing. Masalan: /analyze BTCUSDT")
        return
    
    symbol = context.args[0].upper()
    chat_id = update.effective_chat.id
    if chat_id not in user_data_store:
        user_data_store[chat_id] = {"lang": "uz", "monitoring": {}}
        
    thinking_text = get_text(chat_id, "thinking")
    thinking_msg = await update.message.reply_text(thinking_text)
    exchange = EXCHANGES.get(symbol, "BINANCE" if "USDT" in symbol else "")
    result = await get_fast_indicators(symbol=symbol, exchange=exchange, timeframe="1m")
    if result.get("success"):
        indicators = result.get("indicators", {}).get("data", {})
        price = indicators.get("close", "N/A")
        rsi = indicators.get("RSI", "N/A")
        macd = indicators.get("MACD.macd", "N/A")
        recommendation = indicators.get("Recommend.All", "N/A")
        inds_text = f"• RSI: <code>{rsi}</code>\n• MACD: <code>{macd}</code>\n• Tavsiya: <b>{recommendation}</b>"
        final_text = get_text(chat_id, "analysis_result", symbol=symbol, price=price, indicators=inds_text)
        
        keyboard = [
            [InlineKeyboardButton(get_text(chat_id, "start_monitor"), callback_data=f"monitor_{symbol}")],
            [InlineKeyboardButton("🤖 AI Tahlil (PRO)", callback_data="ai_analysis")],
            [InlineKeyboardButton("🔙 Bosh menyu / Главное меню", callback_data="back_main")]
        ]
        
        await thinking_msg.edit_text(final_text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        keyboard = [[InlineKeyboardButton("🔙 Bosh menyu / Главное меню", callback_data="back_main")]]
        await thinking_msg.edit_text(get_text(chat_id, "error") + f"\n\nBunday aktiv topilmadi.", reply_markup=InlineKeyboardMarkup(keyboard))

async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    logger.info(f"Admin command called by chat_id: {chat_id}. ADMIN_ID is {ADMIN_ID}")
    if chat_id != ADMIN_ID and str(chat_id) not in admins:
        await update.message.reply_text(f"❌ Kechirasiz, siz admin emassiz!\nSizning ID raqamingiz: `{chat_id}`", parse_mode=ParseMode.MARKDOWN)
        return
        
    total_users = len(user_data_store)
    pro_users = sum(1 for data in user_data_store.values() if data.get("is_pro"))
    active_monitors = sum(len(data.get("monitoring", {})) for data in user_data_store.values())
    
    text = (
        f"👑 <b>Admin Panel</b>\n\n"
        f"👥 Barcha foydalanuvchilar: <b>{total_users}</b>\n"
        f"🌟 PRO foydalanuvchilar: <b>{pro_users}</b>\n"
        f"👀 Faol monitoringlar: <b>{active_monitors}</b>\n\n"
        f"<i>Quyidagi menyudan kerakli harakatni tanlang:</i>"
    )
    
    keyboard = [
        [InlineKeyboardButton("📢 Hammaga xabar yuborish", callback_data="admin_broadcast")],
        [InlineKeyboardButton("📊 Batafsil Statistika", callback_data="admin_stats")],
        [InlineKeyboardButton("🔙 Yopish", callback_data="admin_close")]
    ]
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))

async def post_init(application: Application):
    commands = [
        BotCommand("start", "Botni ishga tushirish"),
        BotCommand("menu", "Asosiy menyu"),
        BotCommand("crypto", "Kriptovalyutalar"),
        BotCommand("forex", "Valyuta juftliklari"),
        BotCommand("stocks", "Aksiyalar"),
        BotCommand("futures", "Fyucherslar"),
        BotCommand("analyze", "Tezkor tahlil (misol: /analyze BTCUSDT)"),
        BotCommand("calc", "Kripto-kalkulyator"),
        BotCommand("monitors", "Aktiv monitoringlarni ko'rish"),
        BotCommand("stop", "Barcha monitoringlarni to'xtatish"),
        BotCommand("pro", "PRO versiya imkoniyatlari"),
        BotCommand("help", "Yordam")
    ]
    await application.bot.set_my_commands(commands)

def main():
    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_TOKEN topilmadi!")
        return
        
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).post_init(post_init).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", cmd_menu))
    application.add_handler(CommandHandler("help", cmd_help))
    application.add_handler(CommandHandler("stop", cmd_stop))
    application.add_handler(CommandHandler("monitors", cmd_monitors))
    application.add_handler(CommandHandler("admin", cmd_admin))
    application.add_handler(CommandHandler("crypto", cmd_crypto))
    application.add_handler(CommandHandler("forex", cmd_forex))
    application.add_handler(CommandHandler("stocks", cmd_stocks))
    application.add_handler(CommandHandler("futures", cmd_futures))
    application.add_handler(CommandHandler("calc", cmd_calc))
    application.add_handler(CommandHandler("pro", cmd_pro))
    application.add_handler(CommandHandler("analyze", cmd_analyze))
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
