import httpx
import asyncio

async def get_indicators_fast(symbol: str, exchange: str, timeframe: str = "1m"):
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
        resp = await client.post(url, json=payload)
        data = resp.json()
        print(f"{symbol}:", data)

async def main():
    await get_indicators_fast("BTCUSDT", "BINANCE", "1m")
    await get_indicators_fast("EURUSD", "FX_IDC", "1m")
    await get_indicators_fast("AAPL", "NASDAQ", "1m")

asyncio.run(main())
